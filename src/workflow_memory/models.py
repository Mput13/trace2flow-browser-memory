from typing import Any

from pydantic import BaseModel, Field


class RunArtifact(BaseModel):
    run_id: str
    site: str
    task_family: str
    run_mode: str
    status: str
    task_input: dict[str, Any]
    metrics: dict[str, Any] = Field(default_factory=dict)
