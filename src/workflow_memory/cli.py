import json
from pathlib import Path
from typing import Optional

import typer

from workflow_memory.config import load_config
from workflow_memory.pipeline.baseline import run_baseline, run_task
from workflow_memory.pipeline.memory_run import run_memory_task
from workflow_memory.pipeline.optimize import run_optimize
from workflow_memory.pipeline.task_suite import load_task_suite

app = typer.Typer(help="Workflow memory CLI")


def _not_implemented(command_name: str) -> None:
    typer.echo(f"{command_name} is not implemented yet.")
    raise typer.Exit(code=1)


def _output_result(result: dict, output_json: bool) -> None:
    if output_json:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        typer.echo(f"run_id: {result['run_id']}")
        typer.echo(f"status: {result['status']}")
        typer.echo(f"action_count: {result['action_count']}")
        typer.echo(f"elapsed_seconds: {result['elapsed_seconds']:.2f}")


# ---------------------------------------------------------------------------
# run — primary command
# ---------------------------------------------------------------------------

@app.command("run")
def run(
    task: str = typer.Option(..., "--task", help="Natural-language task description"),
    site: Optional[str] = typer.Option(
        None, "--site",
        help="Optional site tag for memory grouping (e.g. mai_schedule). "
             "If omitted, site is inferred from any URL in the task string.",
    ),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Agent step budget"),
    output_json: bool = typer.Option(False, "--output", help="Output as JSON"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run browser headless (default) or visible"),
) -> None:
    """Run a browser task with a natural-language task string."""
    from workflow_memory.runtime.browser_runner import BrowserRunner
    cfg = load_config(config_path)
    runner = BrowserRunner.from_config(cfg, headless=headless)
    result = run_task(task=task, config=cfg, site=site, max_steps=max_steps, runner=runner)
    _output_result(result, output_json)


# ---------------------------------------------------------------------------
# run-suite — run every case in a YAML suite
# ---------------------------------------------------------------------------

@app.command("run-suite")
def run_suite(
    suite_path: Path = typer.Option(..., "--suite", help="Path to task suite YAML"),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Agent step budget per case"),
    output_json: bool = typer.Option(False, "--output", help="Output as JSON"),
) -> None:
    """Run every case in a task suite YAML."""
    cfg = load_config(config_path)
    suite = load_task_suite(suite_path)
    total = len(suite.cases)
    successes = 0
    failures = 0
    results = []

    for i, case in enumerate(suite.cases, start=1):
        try:
            result = run_task(
                task=case.task,
                config=cfg,
                site=suite.site,
                task_family=suite.task_family or "",
                max_steps=max_steps,
            )
            status = result["status"]
            results.append({**result, "case_id": case.case_id})
            if not output_json:
                typer.echo(
                    f"[{i}/{total}] case_id={case.case_id} run_id={result['run_id']} "
                    f"status={status} actions={result['action_count']} "
                    f"elapsed={result['elapsed_seconds']:.2f}s"
                )
            successes += status == "succeeded"
            failures += status != "succeeded"
        except Exception as exc:
            failures += 1
            results.append({"case_id": case.case_id, "status": "error", "error": str(exc)})
            if not output_json:
                typer.echo(
                    f"[{i}/{total}] case_id={case.case_id} ERROR: {type(exc).__name__}: {exc}",
                    err=True,
                )

    if output_json:
        typer.echo(json.dumps(
            {"total": total, "succeeded": successes, "failed": failures, "results": results},
            indent=2, ensure_ascii=False,
        ))
    else:
        typer.echo(f"Suite complete: total={total} succeeded={successes} failed={failures}")


# ---------------------------------------------------------------------------
# baseline — legacy command (backward compat)
# ---------------------------------------------------------------------------

@app.command("baseline")
def baseline(
    site: str = typer.Option(..., "--site", help="Site identifier"),
    task_family: str = typer.Option(..., "--task-family", help="Task family identifier"),
    input_json: str = typer.Option("{}", "--input", help="JSON-encoded task input"),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Agent step budget"),
    output_json: bool = typer.Option(False, "--output", help="Output as JSON"),
) -> None:
    """Run a baseline browser job (legacy structured-input interface)."""
    try:
        task_input = json.loads(input_json)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON for --input: {exc}", err=True)
        raise typer.Exit(code=2)

    cfg = load_config(config_path)
    result = run_baseline(
        site=site, task_family=task_family, task_input=task_input,
        config=cfg, max_steps=max_steps,
    )
    _output_result(result, output_json)


# ---------------------------------------------------------------------------
# baseline-suite — legacy suite command (backward compat)
# ---------------------------------------------------------------------------

@app.command("baseline-suite")
def baseline_suite(
    suite_path: Path = typer.Option(..., "--suite", help="Path to task suite YAML"),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Agent step budget per input"),
) -> None:
    """Run baseline against every case in a task suite YAML (legacy command)."""
    cfg = load_config(config_path)
    suite = load_task_suite(suite_path)
    total = len(suite.cases)
    successes = 0
    failures = 0
    for i, case in enumerate(suite.cases, start=1):
        try:
            result = run_task(
                task=case.task,
                config=cfg,
                site=suite.site,
                task_family=suite.task_family or "",
                max_steps=max_steps,
            )
            status = result["status"]
            typer.echo(
                f"[{i}/{total}] run_id={result['run_id']} status={status} "
                f"actions={result['action_count']} elapsed={result['elapsed_seconds']:.2f}s"
            )
            successes += status == "succeeded"
            failures += status != "succeeded"
        except Exception as exc:
            failures += 1
            typer.echo(f"[{i}/{total}] ERROR: {type(exc).__name__}: {exc}", err=True)
    typer.echo(f"Suite complete: total={total} succeeded={successes} failed={failures}")


# ---------------------------------------------------------------------------
# optimize / memory-run / eval-batch — stubs
# ---------------------------------------------------------------------------

@app.command("optimize")
def optimize(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to optimize"),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
) -> None:
    """Run optimization pass on a completed baseline run."""
    cfg = load_config(config_path)
    result = run_optimize(run_id=run_id, config=cfg)
    if result["admitted"]:
        typer.echo(f"memory_id: {result['memory_id']}")
        typer.echo(f"site: {result['site']}")
    else:
        typer.echo(f"Not admitted: {result.get('reason', 'unknown')}")


@app.command("memory-run")
def memory_run(
    task: Optional[str] = typer.Option(None, "--task", help="Natural-language task"),
    site: Optional[str] = typer.Option(None, "--site", help="Optional site tag"),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Agent step budget"),
    output_json: bool = typer.Option(False, "--output", help="Output as JSON"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run browser headless (default) or visible"),
) -> None:
    """Run a task with admitted memory hints."""
    from workflow_memory.runtime.browser_runner import BrowserRunner
    if task is None:
        typer.echo("Error: --task is required.", err=True)
        raise typer.Exit(code=2)
    cfg = load_config(config_path)
    runner = BrowserRunner.from_config(cfg, headless=headless)
    result = run_memory_task(task=task, config=cfg, site=site, max_steps=max_steps, runner=runner)
    _output_result(result, output_json)
    if not output_json:
        used = result.get("memory_used", False)
        mid = result.get("memory_id")
        typer.echo(f"memory_used: {used}" + (f" ({mid})" if mid else ""))


@app.command("eval-batch")
def eval_batch(
    suite: str = typer.Option(..., "--suite", help="Path to task suite YAML"),
    config_path: Path = typer.Option(
        Path("config/project.yaml"), "--config", help="Path to project.yaml"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Agent step budget per case"),
    output_json: bool = typer.Option(False, "--output", help="Output as JSON"),
) -> None:
    """Run an evaluation suite (baseline vs memory comparison)."""
    from workflow_memory.eval.batch import run_eval_suite
    from workflow_memory.eval.reporting import summarize_comparison

    cfg = load_config(config_path)
    results = run_eval_suite(Path(suite), cfg, max_steps=max_steps)
    summary = summarize_comparison(results)
    if output_json:
        typer.echo(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        typer.echo(f"Cases:            {summary['total_cases']}")
        typer.echo(f"Baseline success: {summary['baseline_success_rate']:.0%}")
        typer.echo(f"Memory success:   {summary['memory_success_rate']:.0%}")
        typer.echo(f"Avg action delta: {summary['avg_action_delta']:.1f}")
        typer.echo(f"Memory used in:   {summary['memory_used_count']} cases")
