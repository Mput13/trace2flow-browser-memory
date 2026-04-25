"""Tests for retrieval/scoring.py and retrieval/hints.py."""
from workflow_memory.retrieval.scoring import score_candidate
from workflow_memory.retrieval.hints import format_hint_packet


# ---------------------------------------------------------------------------
# score_candidate
# ---------------------------------------------------------------------------

def test_score_candidate_identical_tasks_returns_1() -> None:
    task = "Найди расписание группы М8О-105БВ-25 на понедельник"
    score = score_candidate(task, task)
    assert score == 1.0


def test_score_candidate_completely_different_tasks_returns_low() -> None:
    score = score_candidate(
        "Find campsite near Yosemite",
        "Найди расписание группы М8О-105БВ-25",
    )
    assert score < 0.5


def test_score_candidate_similar_tasks_returns_high() -> None:
    score = score_candidate(
        "Найди расписание группы М8О-105БВ-25 на текущую неделю",
        "Найди расписание группы М8О-105БВ-25 на эту неделю",
    )
    assert score >= 0.7


def test_score_candidate_returns_float_in_range() -> None:
    score = score_candidate("task A", "task B")
    assert 0.0 <= score <= 1.0


def test_score_candidate_threshold_param_accepted() -> None:
    # threshold is informational, doesn't filter — just verify it's accepted
    score = score_candidate("task A", "task A", threshold=0.9)
    assert score == 1.0


# ---------------------------------------------------------------------------
# format_hint_packet
# ---------------------------------------------------------------------------

def test_format_hint_packet_has_required_keys() -> None:
    memory_entry = {
        "workflow_summary": "Navigate to schedule page, select group",
        "likely_path": ["go to groups.php", "select group", "read schedule"],
        "page_hints": ["schedule table visible"],
        "success_cues": ["time slot shown"],
        "mismatch_signals": ["group not found"],
    }
    packet = format_hint_packet(memory_entry)
    assert "goal" in packet
    assert "likely_path" in packet
    assert "page_hints" in packet
    assert "success_cues" in packet
    assert "mismatch_signals" in packet


def test_format_hint_packet_goal_from_workflow_summary() -> None:
    memory_entry = {
        "workflow_summary": "Find schedule",
        "likely_path": [],
        "page_hints": [],
        "success_cues": [],
        "mismatch_signals": [],
    }
    packet = format_hint_packet(memory_entry)
    assert packet["goal"] == "Find schedule"


def test_format_hint_packet_handles_missing_keys_gracefully() -> None:
    packet = format_hint_packet({})
    assert packet["goal"] == ""
    assert packet["likely_path"] == []
