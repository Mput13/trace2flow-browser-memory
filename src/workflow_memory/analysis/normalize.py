"""Action history normalization utilities."""
from typing import Any


def normalize_action_history(action_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize an agent action history to a canonical form.

    Args:
        action_history: Raw action history from the browser agent.

    Returns:
        List of normalized action dicts with consistent keys.
    """
    normalized = []
    for item in action_history:
        normalized.append(
            {
                "action": item.get("action", "unknown"),
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "labels": item.get("labels", []),
            }
        )
    return normalized
