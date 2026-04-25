"""Tests for pipeline/baseline.py (run_task) with fully mocked browser runner."""
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from workflow_memory.config import ProjectConfig, AdmissionConfig, RetrievalConfig, ParallelismConfig
from workflow_memory.pipeline.baseline import derive_status, get_adapter, run_task
from workflow_memory.runtime.browser_runner import BrowserRunResult


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

class FakeHistory:
    """Minimal stand-in for AgentHistoryList."""

    def __init__(
        self,
        done: bool = True,
        successful: bool | None = True,
        steps: int = 5,
        action_names_val: list[str] | None = None,
        final: str | None = "09:00 Лекция, ауд. 301",
        errors_val: list[str | None] | None = None,
        urls_val: list[str | None] | None = None,
        dump: dict[str, Any] | None = None,
    ) -> None:
        self._done = done
        self._successful = successful
        self._steps = steps
        self._action_names = action_names_val or ["navigate", "extract"]
        self._final = final
        self._errors = errors_val or [None]
        self._urls = urls_val or ["https://mai.ru/education/studies/schedule/groups.php"]
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

    def total_duration_seconds(self) -> float:
        return 1.0


class FakeBrowserRunner:
    """Stub BrowserRunner that returns a FakeHistory without touching the network."""

    def __init__(self, history: FakeHistory | None = None, elapsed: float = 1.23) -> None:
        self._history = history or FakeHistory()
        self._elapsed = elapsed

    def run(self, task_prompt: str, max_steps: int = 25) -> BrowserRunResult:
        return BrowserRunResult(history=self._history, elapsed_seconds=self._elapsed)


class ErrorBrowserRunner:
    """Stub BrowserRunner that raises an exception."""

    def run(self, task_prompt: str, max_steps: int = 25) -> BrowserRunResult:
        raise RuntimeError("boom")


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
        retrieval=RetrievalConfig(
            fuzzy_threshold=0.75,
        ),
        parallelism=ParallelismConfig(max_workers=2),
    )


_TASK = "Найди расписание группы М8О-105БВ-25 на текущую неделю, понедельник"


# ---------------------------------------------------------------------------
# Test 1: derive_status — done + successful
# ---------------------------------------------------------------------------

def test_derive_status_succeeded() -> None:
    assert derive_status(is_done=True, is_successful=True) == "succeeded"


# ---------------------------------------------------------------------------
# Test 2: derive_status — done + not successful
# ---------------------------------------------------------------------------

def test_derive_status_failed_verification() -> None:
    assert derive_status(is_done=True, is_successful=False) == "failed_verification"


# ---------------------------------------------------------------------------
# Test 3: derive_status — not done (max_steps exhausted)
# ---------------------------------------------------------------------------

def test_derive_status_failed_execution_not_done() -> None:
    assert derive_status(is_done=False, is_successful=None) == "failed_execution"


# ---------------------------------------------------------------------------
# Test 4: get_adapter — known and unknown sites
# ---------------------------------------------------------------------------

def test_get_adapter_known_site_mai() -> None:
    from workflow_memory.site_adapters.mai_schedule import MaiScheduleAdapter
    adapter = get_adapter("mai_schedule")
    assert isinstance(adapter, MaiScheduleAdapter)


def test_get_adapter_known_site_recreation() -> None:
    from workflow_memory.site_adapters.recreation_gov import RecreationGovAdapter
    adapter = get_adapter("recreation_gov")
    assert isinstance(adapter, RecreationGovAdapter)


def test_get_adapter_unknown_site_returns_none() -> None:
    assert get_adapter("unknown_site") is None


def test_get_adapter_none_site_returns_none() -> None:
    assert get_adapter(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test 5: run_task returns expected keys
# ---------------------------------------------------------------------------

def test_run_task_returns_expected_keys(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    result = run_task(
        task=_TASK,
        site="mai_schedule",
        config=cfg,
        runner=FakeBrowserRunner(),
    )
    expected_keys = {
        "run_id", "status", "action_count", "elapsed_seconds",
        "final_result", "agent_success",
        "trace_path", "normalized_path", "result_path",
    }
    assert expected_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# Test 6: run_task writes artifact files to disk
# ---------------------------------------------------------------------------

def test_run_task_writes_artifact_files(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    result = run_task(
        task=_TASK,
        site="mai_schedule",
        config=cfg,
        runner=FakeBrowserRunner(),
    )
    assert Path(result["trace_path"]).exists()
    assert Path(result["normalized_path"]).exists()
    assert Path(result["result_path"]).exists()


# ---------------------------------------------------------------------------
# Test 7: run_task writes a matching DB row
# ---------------------------------------------------------------------------

def test_run_task_writes_db_row(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    result = run_task(
        task=_TASK,
        site="mai_schedule",
        config=cfg,
        runner=FakeBrowserRunner(),
    )
    db_path = tmp_path / "db.sqlite"
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT run_id, site, task_family, run_mode, trace_path "
            "FROM runs WHERE run_id = ?",
            (result["run_id"],),
        ).fetchone()
    assert row is not None
    run_id, site, task_family, run_mode, trace_path = row
    assert run_id == result["run_id"]
    assert site == "mai_schedule"
    assert run_mode == "baseline"
    assert Path(trace_path).exists()


# ---------------------------------------------------------------------------
# Test 8: normalized.json has all required keys
# ---------------------------------------------------------------------------

def test_normalized_json_has_required_keys(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    result = run_task(
        task=_TASK,
        site="mai_schedule",
        config=cfg,
        runner=FakeBrowserRunner(),
    )
    normalized = json.loads(Path(result["normalized_path"]).read_text())
    required_keys = {
        "run_id", "site", "task_family", "task_input", "run_mode", "status",
        "elapsed_seconds", "action_count", "action_names", "final_result",
        "agent_success", "is_done", "errors", "urls_visited",
    }
    assert required_keys.issubset(normalized.keys())


# ---------------------------------------------------------------------------
# Test 9: task_input in DB stores {"task": ..., "site": ...}
# ---------------------------------------------------------------------------

def test_run_task_stores_task_and_site_in_task_input(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    result = run_task(
        task=_TASK,
        site="mai_schedule",
        config=cfg,
        runner=FakeBrowserRunner(),
    )
    normalized = json.loads(Path(result["normalized_path"]).read_text())
    assert normalized["task_input"]["task"] == _TASK
    assert normalized["task_input"]["site"] == "mai_schedule"


# ---------------------------------------------------------------------------
# Test 10: BrowserRunner exception is captured as failed_execution
# ---------------------------------------------------------------------------

def test_run_task_captures_runner_exception(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    result = run_task(
        task=_TASK,
        site="mai_schedule",
        config=cfg,
        runner=ErrorBrowserRunner(),
    )
    assert result["status"] == "failed_execution"
    result_data = json.loads(Path(result["result_path"]).read_text())
    assert "error" in result_data
    assert "RuntimeError" in result_data["error"]


# ---------------------------------------------------------------------------
# Test 11: Two successive calls produce distinct run_ids and artifact dirs
# ---------------------------------------------------------------------------

def test_run_task_produces_distinct_run_ids(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    r1 = run_task(task=_TASK, site="mai_schedule", config=cfg, runner=FakeBrowserRunner())
    r2 = run_task(task=_TASK, site="mai_schedule", config=cfg, runner=FakeBrowserRunner())
    assert r1["run_id"] != r2["run_id"]
    assert r1["trace_path"] != r2["trace_path"]
    assert Path(r1["trace_path"]).exists()
    assert Path(r2["trace_path"]).exists()
