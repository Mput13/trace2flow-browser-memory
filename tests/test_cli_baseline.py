"""Tests for the CLI commands wiring."""
import shutil
from pathlib import Path
from typing import Any

import pytest
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


def _fake_run_task(**kwargs: Any) -> dict[str, Any]:
    return {
        "run_id": "test-id-123",
        "status": "succeeded",
        "action_count": 7,
        "elapsed_seconds": 12.34,
        "final_result": "08:00 Лекция, ауд. 301",
        "agent_success": True,
        "trace_path": "t",
        "normalized_path": "n",
        "result_path": "r",
    }


def _fake_run_baseline(**kwargs: Any) -> dict[str, Any]:
    return {
        "run_id": "test-id-123",
        "status": "succeeded",
        "action_count": 7,
        "elapsed_seconds": 12.34,
        "final_result": "08:00 Math, room 301",
        "agent_success": True,
        "trace_path": "t",
        "normalized_path": "n",
        "result_path": "r",
    }


# ---------------------------------------------------------------------------
# Test: run --help shows options
# ---------------------------------------------------------------------------

def test_run_help_shows_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--task" in result.stdout
    assert "--site" in result.stdout
    assert "--config" in result.stdout


# ---------------------------------------------------------------------------
# Test: run invokes run_task with correct arguments
# ---------------------------------------------------------------------------

def test_run_invokes_run_task(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def recording_stub(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _fake_run_task(**kwargs)

    monkeypatch.setattr("workflow_memory.cli.run_task", recording_stub)
    config_path = _copy_project_yaml(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--task", "Найди расписание группы М8О-105БВ-25 на понедельник",
            "--site", "mai_schedule",
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0, result.stdout + str(result.exception or "")
    assert len(calls) == 1
    assert calls[0]["task"] == "Найди расписание группы М8О-105БВ-25 на понедельник"
    assert calls[0]["site"] == "mai_schedule"
    from workflow_memory.config import ProjectConfig
    assert isinstance(calls[0]["config"], ProjectConfig)


# ---------------------------------------------------------------------------
# Test: run prints summary fields
# ---------------------------------------------------------------------------

def test_run_prints_summary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("workflow_memory.cli.run_task", _fake_run_task)
    config_path = _copy_project_yaml(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--task", "Какие занятия в среду?",
            "--site", "mai_schedule",
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0
    assert "test-id-123" in result.stdout
    assert "succeeded" in result.stdout
    assert "7" in result.stdout
    assert "12.34" in result.stdout


# ---------------------------------------------------------------------------
# Test: baseline --help shows expected flags (backward compat)
# ---------------------------------------------------------------------------

def test_baseline_help_shows_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["baseline", "--help"])
    assert result.exit_code == 0
    assert "--site" in result.stdout
    assert "--task-family" in result.stdout
    assert "--input" in result.stdout
    assert "--config" in result.stdout


# ---------------------------------------------------------------------------
# Test: baseline invokes run_baseline with correct arguments
# ---------------------------------------------------------------------------

def test_baseline_invokes_run_baseline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def recording_stub(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _fake_run_baseline(**kwargs)

    monkeypatch.setattr("workflow_memory.cli.run_baseline", recording_stub)
    config_path = _copy_project_yaml(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "baseline",
            "--site", "mai_schedule",
            "--task-family", "schedule_lookup",
            "--input", '{"group":"М8О-105БВ-25","date":"2026-04-27"}',
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0, result.stdout + str(result.exception or "")
    assert len(calls) == 1
    assert calls[0]["site"] == "mai_schedule"
    assert calls[0]["task_family"] == "schedule_lookup"
    assert calls[0]["task_input"] == {"group": "М8О-105БВ-25", "date": "2026-04-27"}
    from workflow_memory.config import ProjectConfig
    assert isinstance(calls[0]["config"], ProjectConfig)


# ---------------------------------------------------------------------------
# Test: baseline prints summary fields
# ---------------------------------------------------------------------------

def test_baseline_prints_summary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("workflow_memory.cli.run_baseline", _fake_run_baseline)
    config_path = _copy_project_yaml(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "baseline",
            "--site", "mai_schedule",
            "--task-family", "schedule_lookup",
            "--input", '{"group":"X","date":"2026-01-01"}',
            "--config", str(config_path),
        ],
    )
    assert result.exit_code == 0
    assert "test-id-123" in result.stdout
    assert "succeeded" in result.stdout
    assert "7" in result.stdout
    assert "12.34" in result.stdout


# ---------------------------------------------------------------------------
# Test: Malformed --input JSON exits non-zero
# ---------------------------------------------------------------------------

def test_baseline_malformed_json_exits_nonzero(tmp_path: Path) -> None:
    config_path = _copy_project_yaml(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "baseline",
            "--site", "mai_schedule",
            "--task-family", "schedule_lookup",
            "--input", "{not-json}",
            "--config", str(config_path),
        ],
    )
    assert result.exit_code != 0
    combined = result.stdout + (result.output or "")
    assert "JSON" in combined or "json" in combined.lower()


# ---------------------------------------------------------------------------
# Test: Stub commands still exit 1
# ---------------------------------------------------------------------------

def test_stub_commands_still_exit_nonzero() -> None:
    runner = CliRunner()
    # All commands are now implemented. eval-batch requires --suite; invoking
    # without it must exit non-zero (missing required option).
    result = runner.invoke(app, ["eval-batch"])
    assert result.exit_code != 0, "eval-batch without --suite should exit non-zero"

    # memory-run is implemented but requires --task; invoking without it must also fail
    result = runner.invoke(app, ["memory-run"])
    assert result.exit_code != 0, "memory-run without --task should exit non-zero"
