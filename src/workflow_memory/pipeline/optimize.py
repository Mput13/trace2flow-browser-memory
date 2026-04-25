"""Pipeline: optimization pass and admission policy."""
import json
import os
from pathlib import Path
from typing import Any

from uuid_extensions import uuid7str

from workflow_memory.config import ProjectConfig
from workflow_memory.optimization.optimizer import build_hint_packet, run_optimization_pass
from workflow_memory.storage.repository import RunRepository


def _relative_improvement(baseline: float, rerun: float) -> float:
    if baseline <= 0:
        return 0.0
    return (baseline - rerun) / baseline


def _validate_direct_url(direct_url: str | None, urls_visited: list[str], task: str) -> str | None:
    """Return direct_url only if it is a genuine shortcut.

    Rejects the URL when:
    - it is None or empty
    - it equals the first URL visited (no shortcut — agent started there anyway)
    - it appears in the first third of urls_visited (not near the goal)
    """
    if not direct_url or not urls_visited:
        return None
    deduped = list(dict.fromkeys(u for u in urls_visited if u))
    if not deduped:
        return None
    if direct_url == deduped[0]:
        return None
    try:
        pos = deduped.index(direct_url)
        if pos / len(deduped) < 0.4:
            return None
    except ValueError:
        return None
    return direct_url


def should_admit_memory(
    baseline_metrics: dict[str, Any],
    rerun_metrics: dict[str, Any],
    baseline_passed: bool,
    rerun_passed: bool,
    min_relative_improvement: float,
) -> bool:
    """Decide whether the optimized rerun is good enough to admit to memory.

    Args:
        baseline_metrics: Metrics from the baseline run (action_count, elapsed_time, loop_count).
        rerun_metrics: Metrics from the post-optimization rerun.
        baseline_passed: Whether the baseline run was successful.
        rerun_passed: Whether the rerun was successful.
        min_relative_improvement: Minimum fractional improvement required.

    Returns:
        True if the memory should be admitted.
    """
    if not rerun_passed:
        return False
    if baseline_passed and not rerun_passed:
        return False

    improvements = [
        _relative_improvement(
            float(baseline_metrics.get("action_count", 0)),
            float(rerun_metrics.get("action_count", 0)),
        ),
        _relative_improvement(
            float(baseline_metrics.get("elapsed_time", 0)),
            float(rerun_metrics.get("elapsed_time", 0)),
        ),
        _relative_improvement(
            float(baseline_metrics.get("loop_count", 0)),
            float(rerun_metrics.get("loop_count", 0)),
        ),
    ]
    return any(v >= min_relative_improvement for v in improvements)


def run_optimization(
    model_name: str,
    packet: dict[str, Any],
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run the full optimization pass and return a result dict.

    Args:
        model_name: Model identifier.
        packet: Raw analysis packet.
        base_url: Optional base URL for OpenRouter.
        api_key: Optional API key.

    Returns:
        Dict with analysis, optimized_workflow, human_summary.
    """
    response = run_optimization_pass(model_name, packet, base_url=base_url, api_key=api_key)
    return {
        "analysis": response.analysis,
        "optimized_workflow": response.optimized_workflow,
        "human_summary": response.human_summary,
    }


def run_optimize(run_id: str, config: ProjectConfig) -> dict[str, Any]:
    """End-to-end optimize pipeline: read run artifacts, call LLM, store memory.

    Args:
        run_id: ID of the completed run to optimize.
        config: Project configuration.

    Returns:
        Dict with admitted (bool) and either memory_id/site/task or reason.
    """
    # Resolve normalized.json path
    artifacts_root = Path(config.artifacts_root)
    normalized_path = artifacts_root / "runs" / run_id / "normalized.json"

    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))

    task_input = normalized.get("task_input", {})
    task: str = task_input.get("task", "") or normalized.get("task", "")
    site: str = normalized.get("site", "general")
    action_count: int = normalized.get("action_count", 0)
    final_result: Any = normalized.get("final_result", None)
    action_names: list[str] = normalized.get("action_names", [])
    urls_visited: list[str] = normalized.get("urls_visited", [])
    unique_urls = list(dict.fromkeys(urls_visited))

    packet: dict[str, Any] = {
        "task": task,
        "site": site,
        "action_names": action_names,
        "final_result": final_result,
        "action_count": action_count,
        "urls_visited": unique_urls,
    }

    # Resolve LLM credentials from config
    base_url = config.llm_base_url
    api_key = os.environ.get(config.llm_api_key_env or "OPENAI_API_KEY")

    try:
        response = run_optimization_pass(
            config.optimize_model, packet, base_url=base_url, api_key=api_key
        )
    except Exception as exc:
        return {"admitted": False, "reason": f"llm_error: {exc}"}

    # Validate direct_url — only keep it if it's a genuine shortcut
    raw_direct_url = response.optimized_workflow.get("direct_url")
    validated_direct_url = _validate_direct_url(raw_direct_url, unique_urls, task)
    if validated_direct_url != raw_direct_url:
        response.optimized_workflow["direct_url"] = validated_direct_url

    # Build hint packet and store
    hint_packet = build_hint_packet(
        analysis=response.analysis,
        optimized_workflow=response.optimized_workflow,
    )

    memory_id = uuid7str()
    db_path = Path(config.sqlite_path)
    repo = RunRepository(db_path)
    repo.insert_memory(
        memory_id=memory_id,
        site=site,
        task=task,
        task_family=None,
        hint_packet_dict=hint_packet,
        source_run_id=run_id,
        action_count_baseline=action_count,
    )

    for page in response.site_pages:
        repo.upsert_site_page(
            site=site,
            url_pattern=page.url_pattern,
            description=page.description,
            params=page.params,
        )

    return {"admitted": True, "memory_id": memory_id, "site": site, "task": task}
