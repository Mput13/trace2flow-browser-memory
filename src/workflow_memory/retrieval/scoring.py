"""Retrieval scoring for natural-language task matching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rapidfuzz import fuzz

if TYPE_CHECKING:
    from workflow_memory.storage.repository import RunRepository


def score_candidate(
    query_task: str,
    memory_task: str,
    threshold: float = 0.75,
) -> float:
    """Compute a fuzzy similarity score between two natural-language task strings.

    Uses rapidfuzz token_sort_ratio for order-insensitive matching.

    Args:
        query_task: The incoming task string.
        memory_task: The stored memory task string.
        threshold: Minimum score to consider a match (informational only).

    Returns:
        Score in [0.0, 1.0].
    """
    raw = fuzz.token_sort_ratio(query_task, memory_task)
    return raw / 100.0


def retrieve_best_memory(
    task: str,
    site_key: str,
    repo: RunRepository,
    threshold: float = 0.75,
) -> dict | None:
    """Query the memories store and return the best matching memory for a task.

    Args:
        task: Natural-language task string from the incoming request.
        site_key: Site identifier used to filter memories.
        repo: RunRepository instance for DB access.
        threshold: Minimum fuzzy score (inclusive) to consider a match.

    Returns:
        The memory dict with the highest score if score >= threshold, else None.
        Returns None immediately when no memories exist for the given site.
    """
    memories = repo.get_memories_for_site(site_key)
    if not memories:
        return None

    best_memory: dict | None = None
    best_score: float = -1.0

    for memory in memories:
        score = score_candidate(task, memory["task"], threshold)
        if score > best_score:
            best_score = score
            best_memory = memory

    if best_score >= threshold:
        return best_memory
    return None
