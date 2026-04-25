"""Tests for the `run-suite` and `baseline-suite` CLI commands."""
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from workflow_memory.cli import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_project_yaml(tmp_path: Path) -> Path:
    src = Path(__file__).parent.parent / "config" / "project.yaml"
    dst = tmp_path / "project.yaml"
    shutil.copy(src, dst)
    return dst


def _write_cases_yaml(tmp_path: Path, n_cases: int = 2) -> Path:
    data = {
        "site": "mai_schedule",
        "task_family": "schedule_lookup",
        "cases": [
            {
                "case_id": f"mai-00{i}",
                "task": f"Найди расписание группы М8О-10{i}БВ-25 на понедельник",
            }
            for i in range(1, n_cases + 1)
        ],
    }
    p = tmp_path / "suite.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


def _fake_run_task(**kwargs: Any) -> dict[str, Any]:
    task = kwargs.get("task", "x")
    return {
        "run_id": f"test-run-{hash(task) % 1000}",
        "status": "succeeded",
        "action_count": 5,
        "elapsed_seconds": 3.14,
        "final_result": "some result",
        "agent_success": True,
        "trace_path": "t",
        "normalized_path": "n",
        "result_path": "r",
    }


def _fake_run_baseline(**kwargs: Any) -> dict[str, Any]:
    group = kwargs.get("task_input", {}).get("group", "x")
    return {
        "run_id": f"test-run-{group}",
        "status": "succeeded",
        "action_count": 5,
        "elapsed_seconds": 3.14,
        "final_result": "some result",
        "agent_success": True,
        "trace_path": "t",
        "normalized_path": "n",
        "result_path": "r",
    }


# ---------------------------------------------------------------------------
# Test 1: run-suite --help exits 0 and lists expected options
# ---------------------------------------------------------------------------

def test_run_suite_help_exits_0() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["run-suite", "--help"])
    assert result.exit_code == 0, result.output
    assert "--suite" in result.output
    assert "--config" in result.output
    assert "--max-steps" in result.output


# ---------------------------------------------------------------------------
# Test 2: run-suite calls run_task once per case with correct args
# ---------------------------------------------------------------------------

def test_run_suite_calls_run_task_per_case(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[dict[str, Any]] = []

    def recording_stub(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _fake_run_task(**kwargs)

    monkeypatch.setattr("workflow_memory.cli.run_task", recording_stub)
    config_path = _copy_project_yaml(tmp_path)
    suite_path = _write_cases_yaml(tmp_path, n_cases=3)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-suite",
            "--suite", str(suite_path),
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 3
    for call in calls:
        assert call["site"] == "mai_schedule"
        assert call["task_family"] == "schedule_lookup"
        assert isinstance(call["task"], str)
        assert len(call["task"]) > 0
    from workflow_memory.config import ProjectConfig
    assert isinstance(calls[0]["config"], ProjectConfig)


# ---------------------------------------------------------------------------
# Test 3: run-suite prints per-case summary AND final totals
# ---------------------------------------------------------------------------

def test_run_suite_prints_summary_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("workflow_memory.cli.run_task", _fake_run_task)
    config_path = _copy_project_yaml(tmp_path)
    suite_path = _write_cases_yaml(tmp_path, n_cases=2)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-suite",
            "--suite", str(suite_path),
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0
    assert "case_id=" in result.output
    assert "Suite complete:" in result.output
    assert "succeeded=" in result.output
    assert "failed=" in result.output


# ---------------------------------------------------------------------------
# Test 4: If one run_task raises, suite continues and marks it as failed
# ---------------------------------------------------------------------------

def test_run_suite_continues_on_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    call_count = [0]

    def flaky_stub(**kwargs: Any) -> dict[str, Any]:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("simulated crash")
        return _fake_run_task(**kwargs)

    monkeypatch.setattr("workflow_memory.cli.run_task", flaky_stub)
    config_path = _copy_project_yaml(tmp_path)
    suite_path = _write_cases_yaml(tmp_path, n_cases=3)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-suite",
            "--suite", str(suite_path),
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert call_count[0] == 3
    assert "failed=1" in result.output
    assert "succeeded=2" in result.output


# ---------------------------------------------------------------------------
# Test 5: baseline-suite --help exits 0 and lists expected options
# ---------------------------------------------------------------------------

def test_baseline_suite_help_exits_0() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["baseline-suite", "--help"])
    assert result.exit_code == 0, result.output
    assert "--suite" in result.output
    assert "--config" in result.output
    assert "--max-steps" in result.output


# ---------------------------------------------------------------------------
# Test 6: Existing `run` command (single-input path) still works
# ---------------------------------------------------------------------------

def test_existing_run_command_still_works() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--task" in result.output
    assert "--site" in result.output
