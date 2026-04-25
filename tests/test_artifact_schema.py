"""Tests for the artifact schema validator — Tests 1-8."""
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Import the check_artifact_dir function directly for unit tests
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from check_artifact_schema import check_artifact_dir  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures — shared valid payloads
# ---------------------------------------------------------------------------

VALID_TRACE: dict[str, Any] = {"history": [{"action": "navigate", "url": "https://mai.ru"}]}

VALID_NORMALIZED: dict[str, Any] = {
    "run_id": "r1",
    "site": "mai_schedule",
    "task_family": "schedule_lookup",
    "task_input": {"group": "X", "date": "2026-01-01"},
    "run_mode": "baseline",
    "status": "succeeded",
    "elapsed_seconds": 1.5,
    "action_count": 3,
    "action_names": ["navigate", "extract", "done"],
    "final_result": "ok",
    "agent_success": True,
    "is_done": True,
    "errors": [],
    "urls_visited": ["https://mai.ru/..."],
}

VALID_RESULT: dict[str, Any] = {
    "run_id": "r1",
    "status": "succeeded",
    "final_result": "ok",
    "agent_success": True,
    "elapsed_seconds": 1.5,
    "action_count": 3,
}


def _write_artifact_dir(
    base: Path,
    name: str = "run1",
    trace: Any = None,
    normalized: Any = None,
    result: Any = None,
    skip_trace: bool = False,
    skip_normalized: bool = False,
    skip_result: bool = False,
) -> Path:
    run_dir = base / name
    run_dir.mkdir(parents=True, exist_ok=True)
    if not skip_trace:
        (run_dir / "trace.json").write_text(
            json.dumps(trace if trace is not None else VALID_TRACE), encoding="utf-8"
        )
    if not skip_normalized:
        (run_dir / "normalized.json").write_text(
            json.dumps(normalized if normalized is not None else VALID_NORMALIZED),
            encoding="utf-8",
        )
    if not skip_result:
        (run_dir / "result.json").write_text(
            json.dumps(result if result is not None else VALID_RESULT), encoding="utf-8"
        )
    return run_dir


# ---------------------------------------------------------------------------
# Test 1: Valid directory returns (True, [])
# ---------------------------------------------------------------------------

def test_check_valid_dir_returns_true(tmp_path: Path) -> None:
    run_dir = _write_artifact_dir(tmp_path)
    ok, errors = check_artifact_dir(run_dir)
    assert ok is True
    assert errors == []


# ---------------------------------------------------------------------------
# Test 2: Missing trace.json returns (False, errors) mentioning trace.json
# ---------------------------------------------------------------------------

def test_check_missing_trace_returns_false(tmp_path: Path) -> None:
    run_dir = _write_artifact_dir(tmp_path, skip_trace=True)
    ok, errors = check_artifact_dir(run_dir)
    assert ok is False
    assert any("trace.json" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 3: normalized.json missing run_id returns (False, errors) mentioning run_id
# ---------------------------------------------------------------------------

def test_check_normalized_missing_run_id(tmp_path: Path) -> None:
    bad_normalized = {k: v for k, v in VALID_NORMALIZED.items() if k != "run_id"}
    run_dir = _write_artifact_dir(tmp_path, normalized=bad_normalized)
    ok, errors = check_artifact_dir(run_dir)
    assert ok is False
    assert any("run_id" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 4: Invalid status value returns (False, errors)
# ---------------------------------------------------------------------------

def test_check_invalid_status_returns_false(tmp_path: Path) -> None:
    bad_normalized = {**VALID_NORMALIZED, "status": "unknown_status"}
    run_dir = _write_artifact_dir(tmp_path, normalized=bad_normalized)
    ok, errors = check_artifact_dir(run_dir)
    assert ok is False
    assert any("status" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 5: Type mismatch (action_count is a string) returns (False, errors)
# ---------------------------------------------------------------------------

def test_check_type_mismatch_action_count(tmp_path: Path) -> None:
    bad_normalized = {**VALID_NORMALIZED, "action_count": "three"}
    run_dir = _write_artifact_dir(tmp_path, normalized=bad_normalized)
    ok, errors = check_artifact_dir(run_dir)
    assert ok is False
    assert any("action_count" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 6: CLI exits 0 and prints OK for a valid directory
# ---------------------------------------------------------------------------

def test_cli_valid_dir_exits_0(tmp_path: Path) -> None:
    run_dir = _write_artifact_dir(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_artifact_schema.py"), str(run_dir)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


# ---------------------------------------------------------------------------
# Test 7: CLI exits non-zero and prints errors to stderr for an invalid dir
# ---------------------------------------------------------------------------

def test_cli_invalid_dir_exits_nonzero(tmp_path: Path) -> None:
    bad_normalized = {k: v for k, v in VALID_NORMALIZED.items() if k != "run_id"}
    run_dir = _write_artifact_dir(tmp_path, normalized=bad_normalized)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_artifact_schema.py"), str(run_dir)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "run_id" in combined or "BAD" in combined


# ---------------------------------------------------------------------------
# Test 8: CLI accepts artifacts root and iterates every run subdir
# ---------------------------------------------------------------------------

def test_cli_artifacts_root_iterates_runs(tmp_path: Path) -> None:
    # Build an artifacts root with two run directories
    artifacts_root = tmp_path / "artifacts"
    runs_dir = artifacts_root / "runs"
    runs_dir.mkdir(parents=True)

    _write_artifact_dir(runs_dir, name="run-a")
    _write_artifact_dir(runs_dir, name="run-b")

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_artifact_schema.py"), str(artifacts_root)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    # Both runs should appear in output
    assert "run-a" in proc.stdout
    assert "run-b" in proc.stdout
    assert proc.stdout.count("OK") == 2
