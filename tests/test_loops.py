"""Tests for analysis/loops.py."""
from workflow_memory.analysis.loops import count_loop_events


def test_no_loop_events_returns_0() -> None:
    states = [
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
        {"fingerprint": "C", "action": "scroll"},
    ]
    assert count_loop_events(states) == 0


def test_repeated_2step_pattern_returns_1() -> None:
    states = [
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
    ]
    assert count_loop_events(states) == 1


def test_empty_list_returns_0() -> None:
    assert count_loop_events([]) == 0


def test_single_event_returns_0() -> None:
    assert count_loop_events([{"fingerprint": "A", "action": "click"}]) == 0


def test_two_events_no_repeat_returns_0() -> None:
    states = [
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
    ]
    assert count_loop_events(states) == 0


def test_longer_loop_sequence_detected() -> None:
    states = [
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
        {"fingerprint": "C", "action": "scroll"},
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
    ]
    assert count_loop_events(states) == 1
