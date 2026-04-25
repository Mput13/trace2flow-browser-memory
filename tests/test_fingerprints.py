"""Tests for analysis/fingerprints.py."""
from workflow_memory.analysis.fingerprints import page_state_similarity


def test_identical_states_score_1() -> None:
    state = {"url": "https://example.com/groups", "title": "Schedule", "labels": ["Group", "Week"]}
    assert page_state_similarity(state, state) == 1.0


def test_near_identical_states_score_high() -> None:
    left = {"url": "https://example.com/groups", "title": "Schedule", "labels": ["Group", "Week", "Display"]}
    right = {"url": "https://example.com/groups?x=1", "title": "Schedule", "labels": ["Group", "Week", "Display"]}
    assert page_state_similarity(left, right) >= 0.8


def test_different_path_lowers_score() -> None:
    left = {"url": "https://example.com/groups", "title": "Schedule", "labels": ["Group"]}
    right = {"url": "https://example.com/other", "title": "Schedule", "labels": ["Group"]}
    score = page_state_similarity(left, right)
    assert score < 1.0


def test_no_labels_both_empty_scores_full_label_component() -> None:
    left = {"url": "https://example.com/page", "title": "T", "labels": []}
    right = {"url": "https://example.com/page", "title": "T", "labels": []}
    assert page_state_similarity(left, right) == 1.0


def test_disjoint_labels_lowers_score() -> None:
    left = {"url": "https://example.com/page", "title": "T", "labels": ["A", "B"]}
    right = {"url": "https://example.com/page", "title": "T", "labels": ["C", "D"]}
    score = page_state_similarity(left, right)
    assert score < 1.0


def test_score_is_between_0_and_1() -> None:
    left = {"url": "https://a.com", "title": "X", "labels": ["foo"]}
    right = {"url": "https://b.com", "title": "Y", "labels": ["bar"]}
    score = page_state_similarity(left, right)
    assert 0.0 <= score <= 1.0
