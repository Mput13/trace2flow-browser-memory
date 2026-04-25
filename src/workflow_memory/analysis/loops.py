"""Loop detection in agent action histories."""


def count_loop_events(state_events: list[dict]) -> int:
    """Count the number of repeated (fingerprint, action) pair sequences.

    Detects consecutive 2-step patterns that have been seen before.

    Args:
        state_events: List of dicts with 'fingerprint' and 'action' keys.

    Returns:
        Number of loop events detected (0 if no loops).
    """
    seen_patterns: set[tuple[str, str, str, str]] = set()
    loops = 0
    for index in range(len(state_events) - 1):
        if index + 1 >= len(state_events):
            break
        pattern = (
            state_events[index]["fingerprint"],
            state_events[index]["action"],
            state_events[index + 1]["fingerprint"],
            state_events[index + 1]["action"],
        )
        if pattern in seen_patterns:
            loops += 1
            break
        seen_patterns.add(pattern)
    return loops
