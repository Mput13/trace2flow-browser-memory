"""Hint packet formatting for memory-run mode."""
from typing import Any


def format_hint_packet(memory_entry: dict[str, Any]) -> dict[str, Any]:
    """Format a stored memory entry into a hint packet for the agent.

    Args:
        memory_entry: A row from the memory store with workflow fields.

    Returns:
        Structured hint packet for injection into the agent prompt.
    """
    return {
        "goal": memory_entry.get("workflow_summary", ""),
        "likely_path": memory_entry.get("likely_path", []),
        "page_hints": memory_entry.get("page_hints", []),
        "success_cues": memory_entry.get("success_cues", []),
        "mismatch_signals": memory_entry.get("mismatch_signals", []),
    }
