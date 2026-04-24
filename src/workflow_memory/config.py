from pathlib import Path

import yaml
from pydantic import BaseModel


class AdmissionConfig(BaseModel):
    min_relative_improvement: float
    require_no_success_regression: bool


class RetrievalConfig(BaseModel):
    categorical_weight: float
    set_weight: float
    numeric_weight: float
    text_weight: float


class ParallelismConfig(BaseModel):
    max_workers: int


class ProjectConfig(BaseModel):
    judge_model: str
    optimize_model: str
    sqlite_path: str
    artifacts_root: str
    near_identical_threshold: float
    browser_use_version: str
    playwright_browser: str
    admission: AdmissionConfig
    retrieval: RetrievalConfig
    parallelism: ParallelismConfig


def load_config(path: Path) -> ProjectConfig:
    data = yaml.safe_load(path.read_text())
    return ProjectConfig.model_validate(data)
