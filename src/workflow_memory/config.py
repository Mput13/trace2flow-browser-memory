from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdmissionConfig(StrictModel):
    min_relative_improvement: float
    require_no_success_regression: bool


class RetrievalConfig(StrictModel):
    # New interface: fuzzy_threshold for natural-language task retrieval
    fuzzy_threshold: Optional[float] = None
    # Legacy weighted-field retrieval (kept for backward compat)
    categorical_weight: Optional[float] = None
    set_weight: Optional[float] = None
    numeric_weight: Optional[float] = None
    text_weight: Optional[float] = None


class ParallelismConfig(StrictModel):
    max_workers: int


class ProjectConfig(StrictModel):
    # LLM provider config
    llm_provider: str = "openai"
    llm_base_url: Optional[str] = None
    llm_api_key_env: str = "OPENAI_API_KEY"

    # Model names
    judge_model: str
    optimize_model: str

    # Storage
    sqlite_path: str
    artifacts_root: str
    near_identical_threshold: float

    # Sub-configs
    admission: AdmissionConfig
    retrieval: RetrievalConfig
    parallelism: ParallelismConfig


def load_config(path: Path) -> ProjectConfig:
    data = yaml.safe_load(path.read_text())
    return ProjectConfig.model_validate(data)
