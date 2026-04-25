"""Tests for memory-run pipeline: retrieve_best_memory and run_memory_task."""
from __future__ import annotations

import json
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
from workflow_memory.retrieval.scoring import retrieve_best_memory
from workflow_memory.pipeline.memory_run import run_memory_task
from workflow_memory.runtime.browser_runner import BrowserRunResult
from workflow_memory.storage.repository import RunRepository


# ---------------------------------------------------------------------------
# Shared helpers
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


def _make_repo(tmp_path: Path) -> RunRepository:
    db_path = tmp_path / "db.sqlite"
    return RunRepository(db_path)


class FakeHistory:
    """Minimal stand-in for AgentHistoryList."""

    def __init__(
        self,
        done: bool = True,
        successful: bool | None = True,
        steps: int = 3,
        action_names_val: list[str] | None = None,
        final: str | None = "done",
        errors_val: list[str | None] | None = None,
        urls_val: list[str | None] | None = None,
        dump: dict[str, Any] | None = None,
    ) -> None:
        self._done = done
        self._successful = successful
        self._steps = steps
        self._action_names = action_names_val or ["navigate", "click"]
        self._final = final
        self._errors = errors_val or [None]
        self._urls = urls_val or ["https://example.com"]
        self._dump = dump or {"steps": []}

    def is_done(self) -> bool:
        return self._done

    def is_successful(self) -> bool | None:
        return self._successful

    def number_of_steps(self) -> int:
        return self._steps

    def action_names(self) -> list[str]:
        return self._action_names

    def final_result(self) -> str | None:
        return self._final

    def errors(self) -> list[str | None]:
        return self._errors

    def urls(self) -> list[str | None]:
        return self._urls

    def model_dump(self) -> dict[str, Any]:
        return self._dump


class FakeBrowserRunner:
    """Stub BrowserRunner that returns a FakeHistory without touching the network."""

    def __init__(self, history: FakeHistory | None = None, elapsed: float = 0.5) -> None:
        self._history = history or FakeHistory()
        self._elapsed = elapsed

    def run(self, task_prompt: str, max_steps: int = 25) -> BrowserRunResult:
        return BrowserRunResult(history=self._history, elapsed_seconds=self._elapsed)


_SITE = "mai_schedule"
_TASK_STORED = "Найди расписание группы М8О-105БВ-25 на текущую неделю"
_TASK_QUERY = "Найди расписание группы М8О-105БВ-25 на эту неделю"
_TASK_UNRELATED = "buy groceries at the supermarket"

_HINT_PACKET = {
    "goal": "Navigate to schedule",
    "likely_path": ["go to groups.php", "select group"],
    "page_hints": ["schedule table visible"],
    "success_cues": ["time slot shown"],
    "mismatch_signals": [],
}


def _insert_test_memory(repo: RunRepository, site: str = _SITE, task: str = _TASK_STORED) -> str:
    memory_id = "test-mem-001"
    repo.insert_memory(
        memory_id=memory_id,
        site=site,
        task=task,
        task_family="schedule",
        hint_packet_dict=_HINT_PACKET,
        source_run_id="src-run-001",
        action_count_baseline=10,
    )
    return memory_id


# ---------------------------------------------------------------------------
# Test 1: retrieve_best_memory returns match when score >= threshold
# ---------------------------------------------------------------------------

def test_retrieve_best_memory_match(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _insert_test_memory(repo)

    result = retrieve_best_memory(
        task=_TASK_QUERY,
        site_key=_SITE,
        repo=repo,
        threshold=0.75,
    )

    assert result is not None
    assert result["memory_id"] == "test-mem-001"
    assert result["site"] == _SITE


# ---------------------------------------------------------------------------
# Test 2: retrieve_best_memory returns None when score < threshold
# ---------------------------------------------------------------------------

def test_retrieve_best_memory_no_match(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _insert_test_memory(repo)

    result = retrieve_best_memory(
        task=_TASK_UNRELATED,
        site_key=_SITE,
        repo=repo,
        threshold=0.75,
    )

    assert result is None


# ---------------------------------------------------------------------------
# Test 3: retrieve_best_memory returns None when DB is empty
# ---------------------------------------------------------------------------

def test_retrieve_best_memory_empty_db(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    result = retrieve_best_memory(
        task=_TASK_QUERY,
        site_key=_SITE,
        repo=repo,
        threshold=0.75,
    )

    assert result is None


# ---------------------------------------------------------------------------
# Test 4: run_memory_task uses memory when a match exists
# ---------------------------------------------------------------------------

def test_run_memory_task_uses_memory(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)

    # Pre-populate the DB with a relevant memory
    repo = RunRepository(Path(cfg.sqlite_path))
    memory_id = _insert_test_memory(repo)

    fake_runner = FakeBrowserRunner()

    result = run_memory_task(
        task=_TASK_QUERY,
        config=cfg,
        site=_SITE,
        runner=fake_runner,
    )

    assert result["memory_used"] is True
    assert result["memory_id"] == memory_id
    assert "run_id" in result
    assert result["status"] == "succeeded"
    assert result["action_count"] == 3


# ---------------------------------------------------------------------------
# Test 5: run_memory_task falls back to run_task when no memory matches
# ---------------------------------------------------------------------------

def test_run_memory_task_falls_back_no_memory(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)

    fake_runner = FakeBrowserRunner()

    # No memories in DB — should fall back to run_task
    result = run_memory_task(
        task=_TASK_QUERY,
        config=cfg,
        site=_SITE,
        runner=fake_runner,
    )

    assert result["memory_used"] is False
    assert result["memory_id"] is None
    assert "run_id" in result


# ---------------------------------------------------------------------------
# Test 6: run_memory_task falls back when task is too different from stored memory
# ---------------------------------------------------------------------------

def test_run_memory_task_falls_back_unrelated_task(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)

    repo = RunRepository(Path(cfg.sqlite_path))
    _insert_test_memory(repo)

    fake_runner = FakeBrowserRunner()

    result = run_memory_task(
        task=_TASK_UNRELATED,
        config=cfg,
        site=_SITE,
        runner=fake_runner,
    )

    assert result["memory_used"] is False
    assert result["memory_id"] is None


# ---------------------------------------------------------------------------
# Test 7: retrieve_best_memory picks the highest-scoring memory among multiple
# ---------------------------------------------------------------------------

def test_retrieve_best_memory_picks_best(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    # Insert two memories: one closely matching, one less so
    repo.insert_memory(
        memory_id="mem-close",
        site=_SITE,
        task=_TASK_STORED,  # close to _TASK_QUERY
        task_family="schedule",
        hint_packet_dict=_HINT_PACKET,
        source_run_id="run-a",
        action_count_baseline=10,
    )
    repo.insert_memory(
        memory_id="mem-far",
        site=_SITE,
        task="Найди новости на главной странице",  # less similar
        task_family="news",
        hint_packet_dict=_HINT_PACKET,
        source_run_id="run-b",
        action_count_baseline=5,
    )

    result = retrieve_best_memory(
        task=_TASK_QUERY,
        site_key=_SITE,
        repo=repo,
        threshold=0.75,
    )

    assert result is not None
    assert result["memory_id"] == "mem-close"


# ---------------------------------------------------------------------------
# Test 8: run_memory_task memory-run writes DB row with run_mode=memory
# ---------------------------------------------------------------------------

def test_run_memory_task_writes_memory_run_mode_to_db(tmp_path: Path) -> None:
    import sqlite3

    cfg = _make_config(tmp_path)

    repo = RunRepository(Path(cfg.sqlite_path))
    _insert_test_memory(repo)

    fake_runner = FakeBrowserRunner()

    result = run_memory_task(
        task=_TASK_QUERY,
        config=cfg,
        site=_SITE,
        runner=fake_runner,
    )

    assert result["memory_used"] is True

    with sqlite3.connect(cfg.sqlite_path) as con:
        row = con.execute(
            "SELECT run_mode FROM runs WHERE run_id = ?",
            (result["run_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == "memory"
