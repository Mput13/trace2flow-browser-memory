"""Evaluation reporting and summarization."""
from typing import Any


def summarize_comparison(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a list of baseline-vs-memory comparison results.

    Only non-error records (those without an ``"error"`` key) contribute to
    the rate / delta calculations.  Error records are still counted in
    ``total_cases`` and included verbatim in ``cases``.

    Args:
        results: Output of :func:`run_eval_suite`.

    Returns:
        Summary dict with aggregate metrics and the full ``cases`` list.
    """
    total = len(results)
    non_error = [r for r in results if "error" not in r]

    baseline_success = sum(
        1 for r in non_error if r.get("baseline_status") == "succeeded"
    )
    memory_success = sum(
        1 for r in non_error if r.get("memory_status") == "succeeded"
    )

    if total > 0:
        baseline_success_rate = baseline_success / total
        memory_success_rate = memory_success / total
    else:
        baseline_success_rate = 0.0
        memory_success_rate = 0.0

    if non_error:
        avg_action_delta = sum(r["action_delta"] for r in non_error) / len(non_error)
    else:
        avg_action_delta = 0.0

    reduction_pcts = [
        r["action_delta"] / r["baseline_actions"] * 100
        for r in non_error
        if r.get("baseline_actions", 0) > 0
    ]
    avg_action_reduction_pct = (
        sum(reduction_pcts) / len(reduction_pcts) if reduction_pcts else 0.0
    )

    memory_used_count = sum(1 for r in non_error if r.get("memory_used") is True)

    return {
        "total_cases": total,
        "successful_cases": len(non_error),
        "baseline_success_rate": baseline_success_rate,
        "memory_success_rate": memory_success_rate,
        "avg_action_delta": avg_action_delta,
        "avg_action_reduction_pct": avg_action_reduction_pct,
        "memory_used_count": memory_used_count,
        "cases": results,
    }


# ---------------------------------------------------------------------------
# Legacy helpers — kept so that existing tests importing these names continue
# to work unchanged.
# ---------------------------------------------------------------------------


def summarize_eval_metrics(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Summarize evaluation results grouped by site.

    Args:
        results: List of result dicts, each with 'site', 'status', 'action_count'.

    Returns:
        Dict mapping site -> summary dict with total_runs, failures, action_counts.
    """
    summary: dict[str, dict[str, Any]] = {}
    for row in results:
        site = row["site"]
        summary.setdefault(site, {"total_runs": 0, "failures": 0, "action_counts": []})
        summary[site]["total_runs"] += 1
        summary[site]["action_counts"].append(row.get("action_count", 0))
        if row.get("status") != "succeeded":
            summary[site]["failures"] += 1
    return summary


def format_eval_report(summary: dict[str, dict[str, Any]]) -> str:
    """Format a summary dict into a human-readable report string.

    Args:
        summary: Output from summarize_eval_metrics.

    Returns:
        Formatted report string.
    """
    lines = ["Evaluation Report", "=" * 40]
    for site, stats in summary.items():
        total = stats["total_runs"]
        failures = stats["failures"]
        successes = total - failures
        counts = stats["action_counts"]
        avg = sum(counts) / len(counts) if counts else 0.0
        lines.append(f"\nSite: {site}")
        lines.append(f"  Total runs:   {total}")
        lines.append(f"  Succeeded:    {successes}")
        lines.append(f"  Failed:       {failures}")
        lines.append(f"  Avg actions:  {avg:.1f}")
    return "\n".join(lines)
