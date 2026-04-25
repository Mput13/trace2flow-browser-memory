"""Tests for the optimize pipeline: DB schema, repository methods, and run_optimize()."""
import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from workflow_memory.config import (
    AdmissionConfig,
    ParallelismConfig,
    ProjectConfig,
    RetrievalConfig,
)
from workflow_memory.db import initialize_db
from workflow_memory.optimization.optimizer import OptimizationResponse
from workflow_memory.storage.repository import RunRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path) -> ProjectConfig:
    return ProjectConfig(
        llm_provider="openrouter",
        llm_base_url="https://openrouter.ai/api/v1",
        llm_api_key_env="OPENROUTER_API_KEY",
        judge_model="anthropic/claude-3-5-sonnet-20241022",
        optimize_model="openai/gpt-4.1",
        sqlite_path=str(tmp_path / "db.sqlite"),
        artifacts_root=str(tmp_path / "artifacts"),
        near_identical_threshold=0.8,
        admission=AdmissionConfig(
            min_relative_improvement=0.10,
            require_no_success_regression=True,
        ),
        retrieval=RetrievalConfig(fuzzy_threshold=0.75),
        parallelism=ParallelismConfig(max_workers=2),
    )


def _make_optimization_response() -> OptimizationResponse:
    return OptimizationResponse(
        analysis={"wasted_steps": ["back navigation"], "loop_count": 1},
        optimized_workflow={
            "goal": "Complete schedule lookup efficiently",
            "likely_path": ["open schedule", "select group", "read timetable"],
            "page_hints": ["schedule page", "group selector"],
            "success_cues": ["timetable visible"],
            "mismatch_signals": ["error page"],
        },
        human_summary="Removed one unnecessary back-navigation step.",
    )


def _write_normalized(tmp_path: Path, run_id: str, data: dict[str, Any]) -> Path:
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = run_dir / "normalized.json"
    normalized_path.write_text(json.dumps(data), encoding="utf-8")
    return normalized_path


# ---------------------------------------------------------------------------
# Test 1: memories table is created by initialize_db()
# ---------------------------------------------------------------------------

def test_memories_table_created(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    initialize_db(db_path)

    with sqlite3.connect(db_path) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "memories" in tables


# ---------------------------------------------------------------------------
# Test 2: insert_memory + get_memories_for_site round-trip
# ---------------------------------------------------------------------------

def test_insert_and_get_memory(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    repo = RunRepository(db_path)

    hint_packet = {
        "goal": "Find schedule",
        "likely_path": ["step1", "step2"],
        "page_hints": ["schedule page"],
        "success_cues": ["timetable visible"],
        "mismatch_signals": ["error message"],
        "analysis": {},
    }

    repo.insert_memory(
        memory_id="mem-001",
        site="mai_schedule",
        task="Find schedule for group M8O-105",
        task_family="schedule_lookup",
        hint_packet_dict=hint_packet,
        source_run_id="run-001",
        action_count_baseline=12,
    )

    memories = repo.get_memories_for_site("mai_schedule")
    assert len(memories) == 1

    mem = memories[0]
    assert mem["memory_id"] == "mem-001"
    assert mem["site"] == "mai_schedule"
    assert mem["task"] == "Find schedule for group M8O-105"
    assert mem["task_family"] == "schedule_lookup"
    assert mem["source_run_id"] == "run-001"
    assert mem["action_count_baseline"] == 12
    assert mem["admitted_at"] is not None

    # hint_packet_json round-trip
    stored_packet = json.loads(mem["hint_packet_json"])
    assert stored_packet["goal"] == "Find schedule"
    assert stored_packet["likely_path"] == ["step1", "step2"]


def test_get_memories_for_site_returns_empty_for_unknown_site(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    repo = RunRepository(db_path)

    result = repo.get_memories_for_site("nonexistent_site")
    assert result == []


def test_get_memories_for_site_filters_by_site(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    repo = RunRepository(db_path)

    hint = {"goal": "g", "likely_path": [], "page_hints": [], "success_cues": [], "mismatch_signals": [], "analysis": {}}

    repo.insert_memory("mem-a", "site_a", "task a", None, hint, "run-a", 5)
    repo.insert_memory("mem-b", "site_b", "task b", None, hint, "run-b", 7)

    site_a_memories = repo.get_memories_for_site("site_a")
    assert len(site_a_memories) == 1
    assert site_a_memories[0]["memory_id"] == "mem-a"

    site_b_memories = repo.get_memories_for_site("site_b")
    assert len(site_b_memories) == 1
    assert site_b_memories[0]["memory_id"] == "mem-b"


# ---------------------------------------------------------------------------
# Test 3: run_optimize admitted=True path (mocked LLM + filesystem)
# ---------------------------------------------------------------------------

def test_run_optimize_admitted(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    run_id = "run-test-001"

    normalized_data = {
        "run_id": run_id,
        "site": "mai_schedule",
        "task": "Find schedule for group M8O-105BV-25",
        "task_family": "schedule_lookup",
        "task_input": {"task": "Find schedule for group M8O-105BV-25", "site": "mai_schedule"},
        "run_mode": "baseline",
        "status": "succeeded",
        "elapsed_seconds": 3.5,
        "action_count": 8,
        "action_names": ["navigate", "click", "extract"],
        "final_result": "09:00 Лекция, ауд. 301",
        "agent_success": True,
        "is_done": True,
        "errors": [],
        "urls_visited": ["https://mai.ru/education/studies/schedule/"],
    }
    _write_normalized(tmp_path, run_id, normalized_data)

    fake_response = _make_optimization_response()

    with patch(
        "workflow_memory.pipeline.optimize.run_optimization_pass",
        return_value=fake_response,
    ):
        from workflow_memory.pipeline.optimize import run_optimize
        result = run_optimize(run_id=run_id, config=cfg)

    assert result["admitted"] is True
    assert "memory_id" in result
    assert result["site"] == "mai_schedule"
    assert result["task"] == "Find schedule for group M8O-105BV-25"

    # Verify memory was actually stored in the DB
    repo = RunRepository(Path(cfg.sqlite_path))
    memories = repo.get_memories_for_site("mai_schedule")
    assert len(memories) == 1
    assert memories[0]["memory_id"] == result["memory_id"]
    assert memories[0]["source_run_id"] == run_id


# ---------------------------------------------------------------------------
# Test 4: run_optimize admitted=False on LLM failure
# ---------------------------------------------------------------------------

def test_run_optimize_llm_failure(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    run_id = "run-test-002"

    normalized_data = {
        "run_id": run_id,
        "site": "recreation_gov",
        "task": "Find campsite at Yosemite",
        "task_family": "campground_search",
        "task_input": {"task": "Find campsite at Yosemite", "site": "recreation_gov"},
        "run_mode": "baseline",
        "status": "succeeded",
        "elapsed_seconds": 5.0,
        "action_count": 10,
        "action_names": ["navigate", "search", "click", "extract"],
        "final_result": "Site A available",
        "agent_success": True,
        "is_done": True,
        "errors": [],
        "urls_visited": ["https://recreation.gov/"],
    }
    _write_normalized(tmp_path, run_id, normalized_data)

    with patch(
        "workflow_memory.pipeline.optimize.run_optimization_pass",
        side_effect=RuntimeError("connection timeout"),
    ):
        from workflow_memory.pipeline.optimize import run_optimize
        result = run_optimize(run_id=run_id, config=cfg)

    assert result["admitted"] is False
    assert "llm_error" in result["reason"]
    assert "connection timeout" in result["reason"]

    # Nothing should be stored in DB
    repo = RunRepository(Path(cfg.sqlite_path))
    memories = repo.get_memories_for_site("recreation_gov")
    assert len(memories) == 0
