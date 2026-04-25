"""Tests for verification/rules.py and verification/llm_judge.py."""
from workflow_memory.verification.rules import rule_based_verdict
from workflow_memory.verification.llm_judge import build_llm_judge_payload


# ---------------------------------------------------------------------------
# rule_based_verdict
# ---------------------------------------------------------------------------

def test_rule_based_verdict_accepts_all_required_fields() -> None:
    verdict = rule_based_verdict(
        required_fields=["subject", "room", "time"],
        structured_output={"subject": "Math", "room": "A-101", "time": "09:00"},
    )
    assert verdict["passed"] is True
    assert verdict["missing_fields"] == []


def test_rule_based_verdict_rejects_missing_field() -> None:
    verdict = rule_based_verdict(
        required_fields=["subject", "room", "time"],
        structured_output={"subject": "Math", "room": "A-101"},
    )
    assert verdict["passed"] is False
    assert "time" in verdict["missing_fields"]


def test_rule_based_verdict_rejects_empty_value() -> None:
    verdict = rule_based_verdict(
        required_fields=["subject", "room"],
        structured_output={"subject": "", "room": "A-101"},
    )
    assert verdict["passed"] is False
    assert "subject" in verdict["missing_fields"]


def test_rule_based_verdict_empty_required_fields() -> None:
    verdict = rule_based_verdict(
        required_fields=[],
        structured_output={"anything": "value"},
    )
    assert verdict["passed"] is True
    assert verdict["missing_fields"] == []


# ---------------------------------------------------------------------------
# build_llm_judge_payload
# ---------------------------------------------------------------------------

def test_build_llm_judge_payload_has_required_keys() -> None:
    payload = build_llm_judge_payload(
        task_description="Найди расписание группы М8О-105БВ-25 на понедельник",
        structured_output={"subject": "Math", "time": "09:00"},
        action_history=[{"action": "navigate", "url": "https://mai.ru"}],
    )
    assert "task_description" in payload
    assert "structured_output" in payload
    assert "action_history" in payload
    assert payload["mode"] == "webjudge-inspired"


def test_build_llm_judge_payload_preserves_task() -> None:
    task = "Find campsite near Yosemite"
    payload = build_llm_judge_payload(
        task_description=task,
        structured_output={},
        action_history=[],
    )
    assert payload["task_description"] == task
