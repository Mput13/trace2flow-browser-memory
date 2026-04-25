"""Tests for the MaiScheduleAdapter site adapter (new natural-language interface)."""
from pathlib import Path

import pytest
import yaml

from workflow_memory.site_adapters.mai_schedule import MaiScheduleAdapter


@pytest.fixture
def adapter() -> MaiScheduleAdapter:
    return MaiScheduleAdapter()


# Test 1: site_id and entrypoint_url
def test_adapter_site_id() -> None:
    assert MaiScheduleAdapter.site_id == "mai_schedule"


def test_adapter_entrypoint_url_contains_groups_php() -> None:
    assert "groups.php" in MaiScheduleAdapter.entrypoint_url


def test_adapter_supports_auth_is_false() -> None:
    # No supports_auth attribute means it's a public adapter (no auth needed)
    assert not hasattr(MaiScheduleAdapter, "supports_auth") or not getattr(MaiScheduleAdapter, "supports_auth", True)


# Test 2: build_task_prompt returns string with URL and task
def test_build_task_prompt_contains_url(adapter: MaiScheduleAdapter) -> None:
    prompt = adapter.build_task_prompt("Найди расписание группы М8О-105БВ-25 на понедельник")
    assert isinstance(prompt, str)
    assert "https://mai.ru/education/studies/schedule/groups.php" in prompt


def test_build_task_prompt_contains_task(adapter: MaiScheduleAdapter) -> None:
    task = "Найди расписание группы М8О-105БВ-25 на понедельник"
    prompt = adapter.build_task_prompt(task)
    assert task in prompt


def test_build_task_prompt_non_empty(adapter: MaiScheduleAdapter) -> None:
    prompt = adapter.build_task_prompt("Какие занятия в среду?")
    assert len(prompt) > 50


# Test 3: verify_result returns False for None
def test_verify_result_none_returns_false(adapter: MaiScheduleAdapter) -> None:
    result = adapter.verify_result("any task", None)
    assert result is False


# Test 4: verify_result returns False for empty string
def test_verify_result_empty_string_returns_false(adapter: MaiScheduleAdapter) -> None:
    result = adapter.verify_result("any task", "")
    assert result is False


# Test 5: verify_result returns True for valid schedule-shaped text
def test_verify_result_valid_schedule_returns_true(adapter: MaiScheduleAdapter) -> None:
    result = adapter.verify_result(
        "Найди расписание группы М8О-105БВ-25 на понедельник",
        "09:00 Математика, ауд. 301 - Проф. Иванов; 11:00 Физика, ауд. 202 - Проф. Сидоров",
    )
    assert result is True


# Test 6: verify_result returns False for long string with no time pattern
def test_verify_result_long_no_time_pattern_returns_false(adapter: MaiScheduleAdapter) -> None:
    long_no_time = "A" * 200
    result = adapter.verify_result("any task", long_no_time)
    assert result is False


# Test 7: verify_result returns False for short string with time pattern
def test_verify_result_short_with_time_returns_false(adapter: MaiScheduleAdapter) -> None:
    result = adapter.verify_result("any task", "09:00")
    assert result is False


# Test 8: Loading tasks/mai_schedule.yaml yields correct cases structure
def test_task_suite_yaml_structure() -> None:
    yaml_path = Path(__file__).parent.parent / "tasks" / "mai_schedule.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert data["site"] == "mai_schedule"
    assert data["task_family"] == "schedule_lookup"
    assert isinstance(data["cases"], list)
    assert len(data["cases"]) >= 2
    for case in data["cases"]:
        assert "case_id" in case
        assert "task" in case
        assert isinstance(case["task"], str)
        assert len(case["task"]) > 0
