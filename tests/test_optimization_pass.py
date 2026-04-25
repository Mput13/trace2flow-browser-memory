"""Tests for optimization/optimizer.py."""
from workflow_memory.optimization.optimizer import OptimizationResponse, build_hint_packet


def test_build_hint_packet_contains_required_sections() -> None:
    packet = build_hint_packet(
        analysis={"wasted_steps": ["back navigation"]},
        optimized_workflow={
            "likely_path": ["open results", "apply filters", "open top card"],
            "page_hints": ["results page", "details page"],
            "success_cues": ["required fields visible"],
            "mismatch_signals": ["filters missing"],
        },
    )
    assert "likely_path" in packet
    assert "mismatch_signals" in packet
    assert "page_hints" in packet
    assert "success_cues" in packet
    assert "analysis" in packet


def test_build_hint_packet_uses_goal_from_workflow() -> None:
    packet = build_hint_packet(
        analysis={},
        optimized_workflow={
            "goal": "Find campsite",
            "likely_path": ["step1"],
            "page_hints": [],
            "success_cues": [],
            "mismatch_signals": [],
        },
    )
    assert packet["goal"] == "Find campsite"


def test_build_hint_packet_default_goal() -> None:
    packet = build_hint_packet(
        analysis={},
        optimized_workflow={
            "likely_path": [],
            "page_hints": [],
            "success_cues": [],
            "mismatch_signals": [],
        },
    )
    assert packet["goal"] == "Complete the task efficiently"


def test_optimization_response_model() -> None:
    resp = OptimizationResponse(
        analysis={"wasted_steps": ["back navigation"]},
        optimized_workflow={
            "likely_path": ["step-1"],
            "page_hints": [],
            "success_cues": [],
            "mismatch_signals": [],
        },
        human_summary="Removed one unnecessary branch.",
    )
    assert resp.analysis["wasted_steps"] == ["back navigation"]
    assert resp.human_summary == "Removed one unnecessary branch."
