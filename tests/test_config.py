from pathlib import Path

import pytest
from pydantic import ValidationError

from workflow_memory.config import ProjectConfig, load_config


def test_load_config_reads_defaults(tmp_path) -> None:
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        """
llm_provider: openrouter
llm_base_url: https://openrouter.ai/api/v1
llm_api_key_env: OPENROUTER_API_KEY
judge_model: anthropic/claude-3-5-sonnet-20241022
optimize_model: openai/gpt-4.1
sqlite_path: data/workflow_memory.sqlite
artifacts_root: artifacts
near_identical_threshold: 0.8
admission:
  min_relative_improvement: 0.10
  require_no_success_regression: true
retrieval:
  fuzzy_threshold: 0.75
parallelism:
  max_workers: 2
        """.strip()
    )

    config = load_config(config_path)
    assert isinstance(config, ProjectConfig)
    assert config.judge_model == "anthropic/claude-3-5-sonnet-20241022"
    assert config.llm_provider == "openrouter"
    assert config.llm_base_url == "https://openrouter.ai/api/v1"
    assert config.llm_api_key_env == "OPENROUTER_API_KEY"
    assert config.admission.min_relative_improvement == 0.10


def test_load_config_reads_shipped_project_defaults() -> None:
    config = load_config(Path("config/project.yaml"))
    assert isinstance(config, ProjectConfig)
    assert config.llm_provider == "openrouter"
    assert config.judge_model == "google/gemini-3-flash-preview"
