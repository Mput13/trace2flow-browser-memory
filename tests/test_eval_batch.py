"""Tests for eval/reporting.py and eval/batch.py."""
from pathlib import Path
from unittest.mock import patch

import pytest

from workflow_memory.eval.batch import run_eval_jobs, run_eval_suite
from workflow_memory.eval.reporting import (
    format_eval_report,
    summarize_comparison,
    summarize_eval_metrics,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUITE_PATH = Path(__file__).parent.parent / "tasks" / "mai_schedule.yaml"


def _make_run_result(
    run_id: str = "rid-001",
    status: str = "succeeded",
    action_count: int = 10,
    elapsed: float = 1.0,
) -> dict:
    return {
        "run_id": run_id,
        "status": status,
        "action_count": action_count,
        "elapsed_seconds": elapsed,
        "final_result": None,
        "agent_success": status == "succeeded",
        "trace_path": Path("/tmp/trace.json"),
        "normalized_path": Path("/tmp/normalized.json"),
        "result_path": Path("/tmp/result.json"),
    }


def _make_memory_result(
    run_id: str = "rid-mem-001",
    status: str = "succeeded",
    action_count: int = 6,
    elapsed: float = 0.8,
    memory_used: bool = True,
    memory_id: str | None = "mem-001",
) -> dict:
    result = _make_run_result(run_id=run_id, status=status, action_count=action_count, elapsed=elapsed)
    result["memory_used"] = memory_used
    result["memory_id"] = memory_id
    return result


# ---------------------------------------------------------------------------
# Legacy: summarize_eval_metrics
# ---------------------------------------------------------------------------


def test_summarize_eval_metrics_reports_site_level_counts() -> None:
    summary = summarize_eval_metrics(
        [
            {"site": "recreation_gov", "status": "succeeded", "action_count": 10},
            {"site": "recreation_gov", "status": "succeeded", "action_count": 8},
            {"site": "mai_schedule", "status": "failed_verification", "action_count": 12},
        ]
    )
    assert summary["recreation_gov"]["total_runs"] == 2
    assert summary["mai_schedule"]["failures"] == 1


def test_summarize_eval_metrics_counts_failures_correctly() -> None:
    summary = summarize_eval_metrics(
        [
            {"site": "mai_schedule", "status": "succeeded", "action_count": 5},
            {"site": "mai_schedule", "status": "failed_execution", "action_count": 0},
            {"site": "mai_schedule", "status": "succeeded", "action_count": 7},
        ]
    )
    assert summary["mai_schedule"]["total_runs"] == 3
    assert summary["mai_schedule"]["failures"] == 1


def test_summarize_eval_metrics_empty_list() -> None:
    summary = summarize_eval_metrics([])
    assert summary == {}


def test_summarize_eval_metrics_tracks_action_counts() -> None:
    summary = summarize_eval_metrics(
        [
            {"site": "recreation_gov", "status": "succeeded", "action_count": 10},
            {"site": "recreation_gov", "status": "succeeded", "action_count": 20},
        ]
    )
    assert summary["recreation_gov"]["action_counts"] == [10, 20]


# ---------------------------------------------------------------------------
# Legacy: format_eval_report
# ---------------------------------------------------------------------------


def test_format_eval_report_contains_site_name() -> None:
    summary = {
        "mai_schedule": {"total_runs": 2, "failures": 0, "action_counts": [5, 7]},
    }
    report = format_eval_report(summary)
    assert "mai_schedule" in report
    assert "2" in report


# ---------------------------------------------------------------------------
# Legacy: run_eval_jobs
# ---------------------------------------------------------------------------


def test_run_eval_jobs_returns_same_count() -> None:
    jobs = [{"id": i} for i in range(5)]
    results = run_eval_jobs(jobs, max_workers=2)
    assert len(results) == 5


def test_run_eval_jobs_applies_runner_fn() -> None:
    jobs = [{"value": i} for i in range(3)]
    results = run_eval_jobs(jobs, max_workers=2, runner_fn=lambda j: {**j, "processed": True})
    assert all(r["processed"] is True for r in results)


def test_run_eval_jobs_identity_by_default() -> None:
    jobs = [{"site": "mai_schedule", "status": "succeeded", "action_count": 5}]
    results = run_eval_jobs(jobs, max_workers=1)
    assert results[0] == jobs[0]


# ---------------------------------------------------------------------------
# New: run_eval_suite
# ---------------------------------------------------------------------------


def test_run_eval_suite_produces_comparison(tmp_path) -> None:
    """run_eval_suite returns one comparison dict per case with required keys."""
    baseline_res = _make_run_result(run_id="b-001", status="succeeded", action_count=10)
    optimize_res = {"admitted": True, "memory_id": "mem-001", "site": "mai_schedule"}
    memory_res = _make_memory_result(run_id="m-001", action_count=6)

    with (
        patch("workflow_memory.eval.batch.run_task", return_value=baseline_res) as mock_run,
        patch("workflow_memory.eval.batch.run_optimize", return_value=optimize_res) as mock_opt,
        patch("workflow_memory.eval.batch.run_memory_task", return_value=memory_res) as mock_mem,
    ):
        # Use a minimal config object (ProjectConfig requires several fields).
        from workflow_memory.config import (
            AdmissionConfig,
            ParallelismConfig,
            ProjectConfig,
            RetrievalConfig,
        )

        cfg = ProjectConfig(
            judge_model="gpt-4o",
            optimize_model="gpt-4o",
            sqlite_path=str(tmp_path / "runs.db"),
            artifacts_root=str(tmp_path / "artifacts"),
            near_identical_threshold=0.9,
            admission=AdmissionConfig(
                min_relative_improvement=0.1,
                require_no_success_regression=True,
            ),
            retrieval=RetrievalConfig(fuzzy_threshold=0.75),
            parallelism=ParallelismConfig(max_workers=1),
        )

        results = run_eval_suite(SUITE_PATH, cfg, max_steps=5)

    # mai_schedule.yaml has 3 cases
    assert len(results) == 3

    required_keys = {
        "case_id",
        "task",
        "baseline_status",
        "baseline_actions",
        "baseline_elapsed",
        "memory_status",
        "memory_actions",
        "memory_elapsed",
        "memory_used",
        "action_delta",
    }
    for record in results:
        assert required_keys.issubset(record.keys()), f"Missing keys in {record}"

    # All baselines succeeded → action_delta should be baseline - memory = 10 - 6 = 4
    assert all(r["action_delta"] == 4 for r in results)
    # optimize should have been called once per case (baseline succeeded each time)
    assert mock_opt.call_count == 3


def test_run_eval_suite_skips_optimize_on_failure(tmp_path) -> None:
    """optimize is NOT called when the baseline did not succeed."""
    baseline_res = _make_run_result(run_id="b-fail", status="failed_execution", action_count=0)
    memory_res = _make_memory_result(run_id="m-001", action_count=0, memory_used=False, memory_id=None)

    with (
        patch("workflow_memory.eval.batch.run_task", return_value=baseline_res),
        patch("workflow_memory.eval.batch.run_optimize") as mock_opt,
        patch("workflow_memory.eval.batch.run_memory_task", return_value=memory_res),
    ):
        from workflow_memory.config import (
            AdmissionConfig,
            ParallelismConfig,
            ProjectConfig,
            RetrievalConfig,
        )

        cfg = ProjectConfig(
            judge_model="gpt-4o",
            optimize_model="gpt-4o",
            sqlite_path=str(tmp_path / "runs.db"),
            artifacts_root=str(tmp_path / "artifacts"),
            near_identical_threshold=0.9,
            admission=AdmissionConfig(
                min_relative_improvement=0.1,
                require_no_success_regression=True,
            ),
            retrieval=RetrievalConfig(fuzzy_threshold=0.75),
            parallelism=ParallelismConfig(max_workers=1),
        )

        results = run_eval_suite(SUITE_PATH, cfg, max_steps=5)

    mock_opt.assert_not_called()
    assert all("error" not in r for r in results)


def test_run_eval_suite_records_error_on_exception(tmp_path) -> None:
    """Exceptions in pipeline calls are caught and recorded per case."""
    with (
        patch("workflow_memory.eval.batch.run_task", side_effect=RuntimeError("browser crashed")),
        patch("workflow_memory.eval.batch.run_optimize"),
        patch("workflow_memory.eval.batch.run_memory_task"),
    ):
        from workflow_memory.config import (
            AdmissionConfig,
            ParallelismConfig,
            ProjectConfig,
            RetrievalConfig,
        )

        cfg = ProjectConfig(
            judge_model="gpt-4o",
            optimize_model="gpt-4o",
            sqlite_path=str(tmp_path / "runs.db"),
            artifacts_root=str(tmp_path / "artifacts"),
            near_identical_threshold=0.9,
            admission=AdmissionConfig(
                min_relative_improvement=0.1,
                require_no_success_regression=True,
            ),
            retrieval=RetrievalConfig(fuzzy_threshold=0.75),
            parallelism=ParallelismConfig(max_workers=1),
        )

        results = run_eval_suite(SUITE_PATH, cfg, max_steps=5)

    assert len(results) == 3
    for r in results:
        assert "error" in r
        assert "browser crashed" in r["error"]


# ---------------------------------------------------------------------------
# New: summarize_comparison
# ---------------------------------------------------------------------------


def test_summarize_comparison_calculates_delta() -> None:
    """avg_action_delta is the mean of all action_delta values."""
    results = [
        {
            "case_id": "c1",
            "task": "t1",
            "baseline_status": "succeeded",
            "baseline_actions": 10,
            "baseline_elapsed": 1.0,
            "memory_status": "succeeded",
            "memory_actions": 6,
            "memory_elapsed": 0.8,
            "memory_used": True,
            "memory_id": "m1",
            "optimize_admitted": True,
            "action_delta": 4,
        },
        {
            "case_id": "c2",
            "task": "t2",
            "baseline_status": "succeeded",
            "baseline_actions": 8,
            "baseline_elapsed": 1.2,
            "memory_status": "succeeded",
            "memory_actions": 4,
            "memory_elapsed": 0.6,
            "memory_used": True,
            "memory_id": "m2",
            "optimize_admitted": True,
            "action_delta": 4,
        },
    ]
    summary = summarize_comparison(results)
    assert summary["avg_action_delta"] == pytest.approx(4.0)
    assert summary["total_cases"] == 2
    assert summary["successful_cases"] == 2


def test_summarize_comparison_success_rates() -> None:
    """baseline_success_rate and memory_success_rate reflect actual statuses."""
    results = [
        {
            "case_id": "c1",
            "task": "t1",
            "baseline_status": "succeeded",
            "baseline_actions": 10,
            "baseline_elapsed": 1.0,
            "memory_status": "failed_execution",
            "memory_actions": 0,
            "memory_elapsed": 0.5,
            "memory_used": False,
            "memory_id": None,
            "optimize_admitted": True,
            "action_delta": 10,
        },
        {
            "case_id": "c2",
            "task": "t2",
            "baseline_status": "failed_execution",
            "baseline_actions": 0,
            "baseline_elapsed": 0.5,
            "memory_status": "succeeded",
            "memory_actions": 8,
            "memory_elapsed": 1.0,
            "memory_used": False,
            "memory_id": None,
            "optimize_admitted": False,
            "action_delta": -8,
        },
    ]
    summary = summarize_comparison(results)
    assert summary["baseline_success_rate"] == pytest.approx(0.5)
    assert summary["memory_success_rate"] == pytest.approx(0.5)


def test_summarize_comparison_memory_used_count() -> None:
    """memory_used_count counts only records where memory_used is True."""
    results = [
        {
            "case_id": "c1",
            "task": "t1",
            "baseline_status": "succeeded",
            "baseline_actions": 10,
            "baseline_elapsed": 1.0,
            "memory_status": "succeeded",
            "memory_actions": 6,
            "memory_elapsed": 0.8,
            "memory_used": True,
            "memory_id": "m1",
            "optimize_admitted": True,
            "action_delta": 4,
        },
        {
            "case_id": "c2",
            "task": "t2",
            "baseline_status": "succeeded",
            "baseline_actions": 8,
            "baseline_elapsed": 1.0,
            "memory_status": "succeeded",
            "memory_actions": 8,
            "memory_elapsed": 1.0,
            "memory_used": False,
            "memory_id": None,
            "optimize_admitted": False,
            "action_delta": 0,
        },
        {
            "case_id": "c3",
            "task": "t3",
            "baseline_status": "succeeded",
            "baseline_actions": 12,
            "baseline_elapsed": 1.5,
            "memory_status": "succeeded",
            "memory_actions": 7,
            "memory_elapsed": 0.9,
            "memory_used": True,
            "memory_id": "m3",
            "optimize_admitted": True,
            "action_delta": 5,
        },
    ]
    summary = summarize_comparison(results)
    assert summary["memory_used_count"] == 2


def test_summarize_comparison_empty() -> None:
    """Empty results list returns zero-value summary."""
    summary = summarize_comparison([])
    assert summary["total_cases"] == 0
    assert summary["baseline_success_rate"] == 0.0
    assert summary["avg_action_delta"] == 0.0
    assert summary["memory_used_count"] == 0


def test_summarize_comparison_with_error_records() -> None:
    """Error records are counted in total_cases but excluded from rate calculations."""
    results = [
        {
            "case_id": "c1",
            "task": "t1",
            "baseline_status": "succeeded",
            "baseline_actions": 10,
            "baseline_elapsed": 1.0,
            "memory_status": "succeeded",
            "memory_actions": 6,
            "memory_elapsed": 0.8,
            "memory_used": True,
            "memory_id": "m1",
            "optimize_admitted": True,
            "action_delta": 4,
        },
        {"case_id": "c2", "error": "browser crashed"},
    ]
    summary = summarize_comparison(results)
    assert summary["total_cases"] == 2
    assert summary["successful_cases"] == 1
    # Only 1 non-error case; baseline succeeded → 1/2 = 0.5
    assert summary["baseline_success_rate"] == pytest.approx(0.5)
