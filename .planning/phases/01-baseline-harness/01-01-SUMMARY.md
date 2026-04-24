---
phase: "01"
plan: "01-01"
subsystem: bootstrap
tags: [config, dependencies, runtime-selection]
key-files:
  created:
    - pyproject.toml
    - config/project.yaml
    - .env.example
    - src/workflow_memory/__init__.py
    - src/workflow_memory/config.py
    - src/workflow_memory/cli.py
    - tests/test_config.py
    - tests/test_cli_smoke.py
decisions:
  - Runtime stack locked: browser-use 0.12.6 + Python 3.11-3.12 + Playwright/Chromium
  - Target site: MAI university portal (MAI_USERNAME / MAI_PASSWORD)
  - LLM: gpt-4.1-mini (judge), gpt-4.1 (optimize) via OpenAI
  - Storage: SQLite index + JSON artifact files
  - Config: YAML-based with strict Pydantic validation
metrics:
  completed: 2026-04-25
---

# Plan 01-01: Select Runtime Stack, Target Site, Benchmark Task Family — Summary

**One-liner:** Locked browser-use + OpenAI + MAI portal as the runtime stack and target for all subsequent phases.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | Bootstrap project with dependencies and config | pyproject.toml, config/project.yaml, .env.example, src/workflow_memory/config.py |

## Changes Made

### pyproject.toml
- Declared `browser-use==0.12.6`, `playwright`, `openai`, `langchain-openai`, `pydantic>=2.11.3`, `typer`, `PyYAML`, `rapidfuzz`, `python-dotenv`, `pytest` as dependencies
- Registered CLI entrypoint: `workflow-memory = "workflow_memory.cli:app"`
- Python requirement: `>=3.11,<3.13`

### config/project.yaml
- `judge_model: gpt-4.1-mini`, `optimize_model: gpt-4.1`
- `sqlite_path: data/workflow_memory.sqlite`, `artifacts_root: artifacts`
- `near_identical_threshold: 0.8`, `browser_use_version: 0.12.6`, `playwright_browser: chromium`
- Admission, retrieval weights, parallelism knobs

### src/workflow_memory/config.py
- `ProjectConfig` Pydantic model with `extra="forbid"` for strict validation
- `load_config(path: Path) -> ProjectConfig` loader

### .env.example
- `OPENAI_API_KEY`, `MAI_USERNAME`, `MAI_PASSWORD` templated

### src/workflow_memory/cli.py
- Typer app with stub commands: `baseline`, `optimize`, `memory-run`, `eval-batch`

## Test Results

```
tests/test_config.py::test_load_config_returns_project_config  PASSED
tests/test_cli_smoke.py  PASSED
```

## Deviations from Plan

None — bootstrap executed as designed.
