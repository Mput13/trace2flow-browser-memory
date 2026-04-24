from typing import Any, TypedDict

from pydantic import BaseModel, Field


class RunArtifact(BaseModel):
    run_id: str
    site: str
    task_family: str
    run_mode: str
    status: str
    task_input: dict[str, Any]
    metrics: dict[str, Any] = Field(default_factory=dict)


class ArtifactPaths(TypedDict):
    trace: str
    normalized: str
    result: str


class PersistedRunRecord(TypedDict):
    run_id: str
    site: str
    task_family: str
    run_mode: str
    status: str
    task_input: dict[str, Any]
    metrics: dict[str, Any]
    trace_path: str
    normalized_path: str
    result_path: str
