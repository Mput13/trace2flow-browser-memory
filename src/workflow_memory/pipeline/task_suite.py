"""Task suite YAML loader supporting the 'cases' format.

YAML format:

    site: mai_schedule          # optional — omit to let the agent infer from the task URL
    task_family: schedule_lookup  # optional label
    cases:
      - case_id: mai-001
        task: "Найди расписание группы М8О-105БВ-25 на текущую неделю, понедельник"
"""
from pathlib import Path
from typing import Any

import yaml
from pydantic import ConfigDict, Field

from workflow_memory.config import StrictModel


class TaskSuiteCase(StrictModel):
    model_config = ConfigDict(extra="allow")

    case_id: str = Field(min_length=1)
    task: str = Field(min_length=1)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


class TaskSuite(StrictModel):
    model_config = ConfigDict(extra="allow")

    site: str | None = None
    task_family: str | None = None
    cases: list[TaskSuiteCase] = Field(min_length=1)


def load_task_suite(path: Path) -> TaskSuite:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"Task suite file {path} must contain a mapping, got {type(data).__name__}"
        )
    raw_cases = data.get("cases", [])
    if not isinstance(raw_cases, list):
        raise ValueError(
            f"Task suite 'cases' must be a list, got {type(raw_cases).__name__}"
        )
    return TaskSuite.model_validate(data)


# Legacy shim
class TaskSuiteInput(StrictModel):
    model_config = ConfigDict(extra="allow")

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()
