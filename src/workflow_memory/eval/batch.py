"""Batch evaluation runner — baseline vs memory comparison."""
from pathlib import Path
from typing import Any

from workflow_memory.config import ProjectConfig
from workflow_memory.pipeline.baseline import run_task
from workflow_memory.pipeline.memory_run import run_memory_task
from workflow_memory.pipeline.optimize import run_optimize
from workflow_memory.pipeline.task_suite import load_task_suite


def run_eval_suite(
    suite_path: Path,
    config: ProjectConfig,
    max_steps: int = 25,
) -> list[dict[str, Any]]:
    """Run a task suite in baseline mode then memory mode, collecting comparison data.

    For each case in the suite the function:
    1. Runs a baseline task.
    2. If the baseline succeeded, runs the optimizer to admit a memory entry.
    3. Runs the same task in memory mode.
    4. Collects a comparison dict with per-case metrics.

    Exceptions raised by individual pipeline calls are caught; the affected
    case is recorded with an ``"error"`` key and execution continues.

    Args:
        suite_path: Path to the task suite YAML file.
        config: Project configuration.
        max_steps: Agent step budget passed to each pipeline call.

    Returns:
        List of comparison dicts, one per case.
    """
    suite = load_task_suite(suite_path)
    results: list[dict[str, Any]] = []

    for case in suite.cases:
        try:
            # Step 1 — baseline run
            baseline_result = run_task(
                task=case.task,
                config=config,
                site=suite.site,
                task_family=suite.task_family or "",
                max_steps=max_steps,
            )

            # Step 2 — optional optimization (only if baseline succeeded)
            optimize_result: dict[str, Any] = {"admitted": False}
            if baseline_result["status"] == "succeeded":
                optimize_result = run_optimize(
                    run_id=baseline_result["run_id"],
                    config=config,
                )

            # Step 3 — memory-run
            memory_result = run_memory_task(
                task=case.task,
                config=config,
                site=suite.site,
                task_family=suite.task_family or "",
                max_steps=max_steps,
            )

            # Step 4 — collect comparison dict
            results.append(
                {
                    "case_id": case.case_id,
                    "task": case.task,
                    "baseline_status": baseline_result["status"],
                    "baseline_actions": baseline_result["action_count"],
                    "baseline_elapsed": baseline_result["elapsed_seconds"],
                    "memory_status": memory_result["status"],
                    "memory_actions": memory_result["action_count"],
                    "memory_elapsed": memory_result["elapsed_seconds"],
                    "memory_used": memory_result.get("memory_used", False),
                    "memory_id": memory_result.get("memory_id"),
                    "optimize_admitted": optimize_result.get("admitted", False),
                    "action_delta": (
                        baseline_result["action_count"] - memory_result["action_count"]
                    ),
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"case_id": case.case_id, "error": str(exc)})

    return results


# ---------------------------------------------------------------------------
# Legacy helpers kept for backward compatibility with earlier test suite.
# ---------------------------------------------------------------------------

from concurrent.futures import ThreadPoolExecutor
from typing import Callable


def run_eval_jobs(
    jobs: list[dict[str, Any]],
    max_workers: int,
    runner_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Run a list of evaluation jobs in parallel.

    Args:
        jobs: List of job dicts describing each evaluation case.
        max_workers: Maximum number of parallel workers.
        runner_fn: Optional callable to execute each job. Defaults to identity.

    Returns:
        List of result dicts in the same order as jobs.
    """
    fn = runner_fn if runner_fn is not None else (lambda job: job)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(fn, jobs))
