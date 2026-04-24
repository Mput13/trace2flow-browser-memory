from workflow_memory.config import ProjectConfig, load_config


def test_load_config_reads_defaults(tmp_path) -> None:
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        """
judge_model: gpt-4.1-mini
optimize_model: gpt-4.1
sqlite_path: data/workflow_memory.sqlite
artifacts_root: artifacts
near_identical_threshold: 0.8
browser_use_version: 0.12.6
playwright_browser: chromium
admission:
  min_relative_improvement: 0.10
  require_no_success_regression: true
retrieval:
  categorical_weight: 0.5
  set_weight: 0.2
  numeric_weight: 0.2
  text_weight: 0.1
parallelism:
  max_workers: 2
        """.strip()
    )

    config = load_config(config_path)
    assert isinstance(config, ProjectConfig)
    assert config.judge_model == "gpt-4.1-mini"
    assert config.browser_use_version == "0.12.6"
    assert config.playwright_browser == "chromium"
    assert config.admission.min_relative_improvement == 0.10
