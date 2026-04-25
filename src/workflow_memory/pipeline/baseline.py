"""Pipeline: run_task (formerly run_baseline).

Accepts a natural-language task string and an optional site tag.
If a site adapter is registered, it enriches the prompt and can verify results.
If not, the task string is passed directly to the agent as-is.
"""
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from uuid_extensions import uuid7str

from workflow_memory.config import ProjectConfig
from workflow_memory.models import RunArtifact
from workflow_memory.runtime.browser_runner import BrowserRunner
from workflow_memory.site_adapters.base import SiteAdapter
from workflow_memory.site_adapters.mai_schedule import MaiScheduleAdapter
from workflow_memory.site_adapters.recreation_gov import RecreationGovAdapter
from workflow_memory.storage.artifacts import ArtifactStore
from workflow_memory.storage.repository import RunRepository

_ADAPTER_REGISTRY: dict[str, type[SiteAdapter]] = {
    "mai_schedule": MaiScheduleAdapter,
    "recreation_gov": RecreationGovAdapter,
}

_URL_RE = re.compile(r"https?://[^\s]+")


def _infer_site(task: str) -> str:
    """Extract domain from URL in task, or return 'general'."""
    match = _URL_RE.search(task)
    if match:
        return urlparse(match.group()).netloc.removeprefix("www.")
    return "general"


def get_adapter(site: str) -> SiteAdapter | None:
    cls = _ADAPTER_REGISTRY.get(site)
    return cls() if cls else None


def derive_status(is_done: bool, is_successful: bool | None) -> str:
    if is_done and is_successful is True:
        return "succeeded"
    if is_done and is_successful is False:
        return "failed_verification"
    return "failed_execution"


def run_task(
    task: str,
    config: ProjectConfig,
    site: str | None = None,
    task_family: str = "",
    max_steps: int = 25,
    runner: BrowserRunner | None = None,
) -> dict[str, Any]:
    """Run a browser task with the given natural-language task string.

    Args:
        task: Natural-language task description. May include a URL directly.
        config: Project configuration.
        site: Optional site tag for memory grouping (e.g. 'mai_schedule').
              If a registered adapter exists for this tag, it enriches the
              prompt. If omitted or unregistered, task is passed as-is and
              site is inferred from any URL found in the task.
        task_family: Optional label for grouping (from YAML suite).
        max_steps: Agent step budget.
        runner: Optional BrowserRunner override (for testing).

    Returns:
        Dict with run_id, status, action_count, elapsed_seconds, etc.
    """
    adapter = get_adapter(site) if site else None
    task_prompt = adapter.build_task_prompt(task) if adapter else task
    site_key = site or _infer_site(task)
    run_id = uuid7str()

    artifacts_root = Path(config.artifacts_root)
    sqlite_path = Path(config.sqlite_path)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    store = ArtifactStore(artifacts_root)
    repo = RunRepository(sqlite_path)

    if runner is None:
        runner = BrowserRunner.from_config(config, headless=False)

    error_message: str | None = None
    history = None
    elapsed = 0.0
    try:
        result = runner.run(task_prompt, max_steps=max_steps)
        history = result.history
        elapsed = result.elapsed_seconds
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"

    if history is not None:
        is_done = history.is_done()
        is_successful = history.is_successful()
        status = derive_status(is_done, is_successful)
        action_count = history.number_of_steps()
        action_names = history.action_names()
        final_result = history.final_result()
        errors_list = [e for e in history.errors() if e]
        urls_visited = history.urls()
        trace_payload = history.model_dump()
    else:
        is_done = False
        is_successful = None
        status = "failed_execution"
        action_count = 0
        action_names = []
        final_result = None
        errors_list = [error_message] if error_message else []
        urls_visited = []
        trace_payload = {"error": error_message}

    task_input_record: dict[str, Any] = {"task": task, "site": site_key}

    run = RunArtifact(
        run_id=run_id,
        site=site_key,
        task_family=task_family or site_key,
        run_mode="baseline",
        status=status,
        task_input=task_input_record,
        metrics={"elapsed_seconds": elapsed, "action_count": action_count},
    )

    normalized_payload = {
        "run_id": run_id,
        "site": site_key,
        "task_family": task_family or site_key,
        "task_input": task_input_record,
        "run_mode": "baseline",
        "status": status,
        "elapsed_seconds": elapsed,
        "action_count": action_count,
        "action_names": action_names,
        "final_result": final_result,
        "agent_success": is_successful,
        "is_done": is_done,
        "errors": errors_list,
        "urls_visited": urls_visited,
    }

    result_payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "final_result": final_result,
        "agent_success": is_successful,
        "elapsed_seconds": elapsed,
        "action_count": action_count,
    }
    if error_message is not None:
        result_payload["error"] = error_message

    paths = store.write_run_artifacts(
        run=run,
        trace_payload=trace_payload,
        normalized_payload=normalized_payload,
        result_payload=result_payload,
    )
    run_dir = artifacts_root / "runs" / run_id
    repo.insert_run(run, paths, artifact_dir=run_dir)

    return {
        "run_id": run_id,
        "status": status,
        "final_result": final_result,
        "agent_success": is_successful,
        "elapsed_seconds": elapsed,
        "action_count": action_count,
        "trace_path": paths["trace"],
        "normalized_path": paths["normalized"],
        "result_path": paths["result"],
    }


# ---------------------------------------------------------------------------
# Backward-compat alias
# ---------------------------------------------------------------------------

def run_baseline(
    site: str,
    task_family: str,
    task_input: dict[str, Any],
    config: ProjectConfig,
    max_steps: int = 25,
    runner: BrowserRunner | None = None,
) -> dict[str, Any]:
    if "task" in task_input:
        task = task_input["task"]
    else:
        parts = [f"{k}={v}" for k, v in task_input.items()]
        task = f"Complete {task_family} task on {site}: " + ", ".join(parts)

    return run_task(
        task=task,
        config=config,
        site=site,
        task_family=task_family,
        max_steps=max_steps,
        runner=runner,
    )
