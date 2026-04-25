"""Tests for site adapters: MaiScheduleAdapter and RecreationGovAdapter."""
import pytest

from workflow_memory.site_adapters.mai_schedule import MaiScheduleAdapter
from workflow_memory.site_adapters.recreation_gov import RecreationGovAdapter


# ---------------------------------------------------------------------------
# MaiScheduleAdapter
# ---------------------------------------------------------------------------

def test_mai_adapter_site_id() -> None:
    assert MaiScheduleAdapter.site_id == "mai_schedule"


def test_mai_adapter_entrypoint_url_contains_groups_php() -> None:
    assert "groups.php" in MaiScheduleAdapter.entrypoint_url


def test_mai_adapter_build_task_prompt_contains_url() -> None:
    adapter = MaiScheduleAdapter()
    prompt = adapter.build_task_prompt("Найди расписание группы М8О-105БВ-25 на понедельник")
    assert "https://mai.ru/education/studies/schedule/groups.php" in prompt


def test_mai_adapter_build_task_prompt_contains_task() -> None:
    adapter = MaiScheduleAdapter()
    task = "Какие занятия у группы М8О-105БВ-25 в среду?"
    prompt = adapter.build_task_prompt(task)
    assert task in prompt


def test_mai_adapter_verify_result_true_for_valid_schedule() -> None:
    adapter = MaiScheduleAdapter()
    result = adapter.verify_result(
        "any task",
        "09:00 Математика, ауд. 301 - Проф. Иванов; 11:00 Физика, ауд. 202 - Проф. Сидоров",
    )
    assert result is True


def test_mai_adapter_verify_result_false_for_none() -> None:
    adapter = MaiScheduleAdapter()
    assert adapter.verify_result("any task", None) is False


def test_mai_adapter_verify_result_false_for_no_time() -> None:
    adapter = MaiScheduleAdapter()
    assert adapter.verify_result("any task", "A" * 200) is False


# ---------------------------------------------------------------------------
# RecreationGovAdapter
# ---------------------------------------------------------------------------

def test_recreation_adapter_site_id() -> None:
    assert RecreationGovAdapter.site_id == "recreation_gov"


def test_recreation_adapter_entrypoint_url() -> None:
    assert "recreation.gov" in RecreationGovAdapter.entrypoint_url


def test_recreation_adapter_build_task_prompt_contains_url() -> None:
    adapter = RecreationGovAdapter()
    prompt = adapter.build_task_prompt("Find tent campsites near Yosemite")
    assert "recreation.gov" in prompt


def test_recreation_adapter_build_task_prompt_contains_task() -> None:
    adapter = RecreationGovAdapter()
    task = "Find available tent campsites near Yosemite for two nights in late June 2026"
    prompt = adapter.build_task_prompt(task)
    assert task in prompt


def test_recreation_adapter_verify_result_true_for_valid() -> None:
    adapter = RecreationGovAdapter()
    result = adapter.verify_result(
        "any task",
        "Found 3 available campsites near Yosemite. Campground: Valley View. "
        "Available dates: June 20-22. Site type: tent.",
    )
    assert result is True


def test_recreation_adapter_verify_result_false_for_none() -> None:
    adapter = RecreationGovAdapter()
    assert adapter.verify_result("any task", None) is False


def test_recreation_adapter_verify_result_false_for_short() -> None:
    adapter = RecreationGovAdapter()
    assert adapter.verify_result("any task", "campsite") is False


def test_recreation_adapter_verify_result_false_for_no_keyword() -> None:
    adapter = RecreationGovAdapter()
    assert adapter.verify_result("any task", "A" * 200) is False
