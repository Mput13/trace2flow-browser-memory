"""Pipeline: memory-run mode — run a task with injected memory hints."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from uuid_extensions import uuid7str

from workflow_memory.config import ProjectConfig
from workflow_memory.models import RunArtifact
from workflow_memory.pipeline.baseline import _infer_site, derive_status, run_task
from workflow_memory.retrieval.scoring import retrieve_best_memory
from workflow_memory.runtime.browser_runner import BrowserRunner
from workflow_memory.storage.artifacts import ArtifactStore
from workflow_memory.storage.repository import RunRepository


def prepare_memory_run(task: str, memory_entry: dict[str, Any]) -> dict[str, Any]:
    """Prepare a memory-augmented task run context.

    Args:
        task: Natural-language task string.
        memory_entry: Admitted memory entry with workflow fields.

    Returns:
        Dict with task and hint_packet ready for the browser runner.
    """
    return {
        "task": task,
        "hint_packet": {
            "goal": memory_entry.get("workflow_summary", ""),
            "direct_url": memory_entry.get("direct_url"),
            "likely_path": memory_entry.get("likely_path", []),
            "page_hints": memory_entry.get("page_hints", []),
            "success_cues": memory_entry.get("success_cues", []),
            "mismatch_signals": memory_entry.get("mismatch_signals", []),
        },
    }


def _classify_task(task: str) -> str:
    """Classify task as 'lookup' or 'search'.

    Lookup tasks have a specific target reachable via a direct URL (e.g. "find
    the schedule for group X").  Search tasks iterate over a result set with no
    shortcut URL (e.g. "find ALL books in category Y").

    Returns 'search' or 'lookup'.
    """
    import re
    search_patterns = [
        r"\bнайди все\b", r"\bпокажи все\b", r"\bсписок всех\b",
        r"\bсколько\b", r"\bперечисли\b",
        r"\bfind all\b", r"\blist all\b", r"\bhow many\b",
        r"\bshow all\b", r"\bget all\b",
    ]
    lowered = task.lower()
    for pat in search_patterns:
        if re.search(pat, lowered):
            return "search"
    return "lookup"


def _extract_goal(task: str) -> str:
    """Strip navigation URLs from a task string, keeping only the outcome goal.

    Removes leading 'Зайди на <url> и' / 'Go to <url> and' patterns so the
    agent focuses on WHAT to find rather than WHERE to start when memory hints
    already provide the entry point.
    """
    import re
    cleaned = re.sub(
        r"(?i)(зайди\s+на\s+https?://\S+\s+и\s+|go\s+to\s+https?://\S+\s+and\s+)",
        "",
        task,
        count=1,
    ).strip()
    return cleaned if cleaned else task


def build_memory_prompt(
    task: str,
    hint_packet: dict[str, Any],
    site_pages: list[dict] | None = None,
) -> str:
    task_type = _classify_task(task)
    # Suppress direct_url for search tasks — no shortcut URL exists for "find all X"
    effective_direct = hint_packet.get("direct_url") if task_type == "lookup" else None
    has_direct = bool(effective_direct)

    if has_direct:
        goal = _extract_goal(task)
        lines = [
            "[Memory-assisted run]",
            "",
            f"GOAL: {goal}",
            "",
            "You have navigation hints from a previous successful run on this site.",
            "Try the recommended entry point FIRST — if it already shows the required",
            "information, you are done. You do NOT need to visit every URL mentioned",
            "in the original task description.",
            "",
            f"Original task (for reference — use it to understand WHAT to find): {task}",
            "",
        ]
    else:
        lines = [f"Task: {task}", ""]

    if site_pages:
        lines.append("Known pages on this site (from previous runs):")
        for page in site_pages:
            conf = page.get("confidence", 1.0)
            caveat = " [may have changed — verify]" if conf < 0.5 else ""
            params_str = ""
            if page.get("params"):
                params_str = " | params: " + ", ".join(
                    f"{k}={v}" for k, v in page["params"].items()
                )
            lines.append(f"  {page['url_pattern']}{params_str} — {page['description']}{caveat}")
        lines.append("")

    if effective_direct:
        lines.append(
            f"Recommended entry point (worked in a previous run): {effective_direct}"
        )
        lines.append("")
    if hint_packet.get("likely_path"):
        likely = hint_packet["likely_path"]
        lines.append("Suggested navigation path:")
        if isinstance(likely, list):
            for step in likely:
                lines.append(f"  - {step}")
        else:
            lines.append(f"  {likely}")
        lines.append("")
    if hint_packet.get("page_hints"):
        lines.append("Page hints: " + ", ".join(hint_packet["page_hints"]))
    if hint_packet.get("success_cues"):
        lines.append("Success cues: " + ", ".join(hint_packet["success_cues"]))
    return "\n".join(lines)


def run_memory_task(
    task: str,
    config: ProjectConfig,
    site: str | None = None,
    task_family: str = "",
    max_steps: int = 25,
    runner: BrowserRunner | None = None,
) -> dict[str, Any]:
    """Run a task using a retrieved memory hint if one exists above threshold.

    Workflow:
    1. Determine site_key from explicit ``site`` or by inferring from the task string.
    2. Query the memories table for the best matching memory for that site.
    3. If a memory is found:
       - Deserialise its hint_packet and build an augmented prompt.
       - Execute the browser runner with the augmented prompt.
       - Return result dict with ``memory_used=True`` and the ``memory_id``.
    4. If no memory qualifies, fall back to a plain ``run_task`` call and add
       ``memory_used=False``, ``memory_id=None`` to the result.

    Args:
        task: Natural-language task description.
        config: Project configuration object.
        site: Optional explicit site key.
        task_family: Optional label for grouping.
        max_steps: Agent step budget.
        runner: Optional BrowserRunner override (for testing).

    Returns:
        Dict with run_id, status, action_count, elapsed_seconds, memory_used,
        memory_id, and artifact paths.
    """
    site_key = site or _infer_site(task)

    sqlite_path = Path(config.sqlite_path)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    repo = RunRepository(sqlite_path)

    threshold = config.retrieval.fuzzy_threshold or 0.75
    memory = retrieve_best_memory(task, site_key, repo, threshold)

    if memory is not None:
        hint_packet = json.loads(memory["hint_packet_json"])
        site_pages = repo.get_site_pages(site_key)
        augmented_prompt = build_memory_prompt(task, hint_packet, site_pages)

        run_id = uuid7str()
        artifacts_root = Path(config.artifacts_root)
        store = ArtifactStore(artifacts_root)

        if runner is None:
            runner = BrowserRunner.from_config(config, headless=False)

        error_message: str | None = None
        history = None
        elapsed = 0.0
        t0 = time.monotonic()
        try:
            result = runner.run(augmented_prompt, max_steps=max_steps)
            history = result.history
            elapsed = result.elapsed_seconds
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"
            elapsed = time.monotonic() - t0

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
            run_mode="memory",
            status=status,
            task_input=task_input_record,
            metrics={"elapsed_seconds": elapsed, "action_count": action_count},
        )

        normalized_payload = {
            "run_id": run_id,
            "site": site_key,
            "task_family": task_family or site_key,
            "task_input": task_input_record,
            "run_mode": "memory",
            "status": status,
            "elapsed_seconds": elapsed,
            "action_count": action_count,
            "action_names": action_names,
            "final_result": final_result,
            "agent_success": is_successful,
            "is_done": is_done,
            "errors": errors_list,
            "urls_visited": urls_visited,
            "memory_id": memory["memory_id"],
        }

        result_payload: dict[str, Any] = {
            "run_id": run_id,
            "status": status,
            "final_result": final_result,
            "agent_success": is_successful,
            "elapsed_seconds": elapsed,
            "action_count": action_count,
            "memory_id": memory["memory_id"],
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

        # Post-hoc quality update — measure actual improvement vs baseline
        baseline_actions = memory.get("action_count_baseline") or 0
        if baseline_actions > 0:
            improvement = (baseline_actions - action_count) / baseline_actions
            repo.update_memory_quality(
                memory_id=memory["memory_id"],
                action_count_rerun=action_count,
                improvement_pct=improvement,
            )

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
            "memory_used": True,
            "memory_id": memory["memory_id"],
        }

    # No memory found — fall back to plain run_task
    fallback = run_task(
        task=task,
        config=config,
        site=site,
        task_family=task_family,
        max_steps=max_steps,
        runner=runner,
    )
    fallback["memory_used"] = False
    fallback["memory_id"] = None
    return fallback
