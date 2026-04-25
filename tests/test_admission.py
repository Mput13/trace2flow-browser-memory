"""Tests for pipeline/optimize.py admission policy."""
from workflow_memory.pipeline.optimize import should_admit_memory


def test_should_admit_memory_requires_metric_improvement() -> None:
    admitted = should_admit_memory(
        baseline_metrics={"action_count": 20, "elapsed_time": 100.0, "loop_count": 4},
        rerun_metrics={"action_count": 16, "elapsed_time": 98.0, "loop_count": 4},
        baseline_passed=True,
        rerun_passed=True,
        min_relative_improvement=0.10,
    )
    assert admitted is True


def test_should_admit_memory_rejects_when_rerun_fails() -> None:
    admitted = should_admit_memory(
        baseline_metrics={"action_count": 20, "elapsed_time": 100.0, "loop_count": 4},
        rerun_metrics={"action_count": 10, "elapsed_time": 50.0, "loop_count": 0},
        baseline_passed=True,
        rerun_passed=False,
        min_relative_improvement=0.10,
    )
    assert admitted is False


def test_should_admit_memory_rejects_insufficient_improvement() -> None:
    admitted = should_admit_memory(
        baseline_metrics={"action_count": 20, "elapsed_time": 100.0, "loop_count": 0},
        rerun_metrics={"action_count": 19, "elapsed_time": 99.0, "loop_count": 0},
        baseline_passed=True,
        rerun_passed=True,
        min_relative_improvement=0.10,
    )
    assert admitted is False


def test_should_admit_memory_accepts_loop_count_improvement() -> None:
    admitted = should_admit_memory(
        baseline_metrics={"action_count": 20, "elapsed_time": 100.0, "loop_count": 5},
        rerun_metrics={"action_count": 20, "elapsed_time": 100.0, "loop_count": 0},
        baseline_passed=True,
        rerun_passed=True,
        min_relative_improvement=0.10,
    )
    assert admitted is True


def test_should_admit_memory_rerun_passes_baseline_failed() -> None:
    # If baseline failed and rerun passes, that's still an improvement → admit
    admitted = should_admit_memory(
        baseline_metrics={"action_count": 25, "elapsed_time": 120.0, "loop_count": 6},
        rerun_metrics={"action_count": 15, "elapsed_time": 80.0, "loop_count": 0},
        baseline_passed=False,
        rerun_passed=True,
        min_relative_improvement=0.10,
    )
    assert admitted is True
