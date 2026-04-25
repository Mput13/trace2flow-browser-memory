"""Tests for TaskSuite YAML loader — cases format."""
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from workflow_memory.pipeline.task_suite import TaskSuite, TaskSuiteCase, load_task_suite


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path: Path, data: Any, filename: str = "suite.yaml") -> Path:
    p = tmp_path / filename
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: load_task_suite returns a valid TaskSuite from the real YAML file
# ---------------------------------------------------------------------------

def test_load_real_suite_returns_task_suite() -> None:
    suite_path = Path(__file__).parent.parent / "tasks" / "mai_schedule.yaml"
    suite = load_task_suite(suite_path)
    assert isinstance(suite, TaskSuite)
    assert suite.site == "mai_schedule"
    assert suite.task_family == "schedule_lookup"
    assert len(suite.cases) >= 2


# ---------------------------------------------------------------------------
# Test 2: Each case has case_id and task
# ---------------------------------------------------------------------------

def test_cases_have_case_id_and_task() -> None:
    suite_path = Path(__file__).parent.parent / "tasks" / "mai_schedule.yaml"
    suite = load_task_suite(suite_path)
    for case in suite.cases:
        assert isinstance(case, TaskSuiteCase)
        assert len(case.case_id) > 0
        assert len(case.task) > 0


# ---------------------------------------------------------------------------
# Test 3: YAML missing `site` raises ValidationError
# ---------------------------------------------------------------------------

def test_load_suite_site_optional(tmp_path: Path) -> None:
    data = {
        "task_family": "schedule_lookup",
        "cases": [{"case_id": "mai-001", "task": "Найди расписание"}],
    }
    path = _write_yaml(tmp_path, data)
    suite = load_task_suite(path)
    assert suite.site is None
    assert suite.task_family == "schedule_lookup"


# ---------------------------------------------------------------------------
# Test 4: YAML with cases: [] raises ValidationError (min_length=1)
# ---------------------------------------------------------------------------

def test_load_suite_empty_cases_raises(tmp_path: Path) -> None:
    data = {
        "site": "mai_schedule",
        "task_family": "schedule_lookup",
        "cases": [],
    }
    path = _write_yaml(tmp_path, data)
    with pytest.raises(ValidationError):
        load_task_suite(path)


# ---------------------------------------------------------------------------
# Test 5: TaskSuiteCase.as_dict() returns correct dict
# ---------------------------------------------------------------------------

def test_task_suite_case_as_dict() -> None:
    case = TaskSuiteCase.model_validate({
        "case_id": "mai-001",
        "task": "Найди расписание группы М8О-105БВ-25 на понедельник",
    })
    d = case.as_dict()
    assert d["case_id"] == "mai-001"
    assert d["task"] == "Найди расписание группы М8О-105БВ-25 на понедельник"


# ---------------------------------------------------------------------------
# Test 6: recreation_gov.yaml also loads correctly
# ---------------------------------------------------------------------------

def test_load_recreation_gov_suite() -> None:
    suite_path = Path(__file__).parent.parent / "tasks" / "recreation_gov.yaml"
    suite = load_task_suite(suite_path)
    assert suite.site == "recreation_gov"
    assert suite.task_family == "campground_search"
    assert len(suite.cases) >= 1
    for case in suite.cases:
        assert len(case.task) > 0
