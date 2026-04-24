# Browser Workflow Memory V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible `browser-use` workflow-memory prototype with public benchmarks, strict admission, CLI tool surface, and evaluation outputs ready for the test-task deliverables.

**Architecture:** The implementation keeps `browser-use` as the execution runtime, moves orchestration and persistence into a Python core package, and uses one structured optimization pass for analysis plus workflow synthesis. Public benchmarks (`Recreation.gov` and public MAI schedule) are the default reproducible path, while private authenticated flows stay exploratory and do not block the core claim.

**Tech Stack:** Python 3.11, `browser-use`, Playwright, Typer, Pydantic, PyYAML, SQLite, RapidFuzz, OpenAI API, pytest, uv

---

## Planned File Structure

### Root Files

- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `README.md`
- Create: `config/project.yaml`

### Package Files

- Create: `src/workflow_memory/__init__.py`
- Create: `src/workflow_memory/cli.py`
- Create: `src/workflow_memory/config.py`
- Create: `src/workflow_memory/models.py`
- Create: `src/workflow_memory/db.py`
- Create: `src/workflow_memory/runtime/browser_runner.py`
- Create: `src/workflow_memory/runtime/sessions.py`
- Create: `src/workflow_memory/storage/artifacts.py`
- Create: `src/workflow_memory/storage/repository.py`
- Create: `src/workflow_memory/site_adapters/base.py`
- Create: `src/workflow_memory/site_adapters/recreation_gov.py`
- Create: `src/workflow_memory/site_adapters/mai_schedule.py`
- Create: `src/workflow_memory/analysis/normalize.py`
- Create: `src/workflow_memory/analysis/fingerprints.py`
- Create: `src/workflow_memory/analysis/loops.py`
- Create: `src/workflow_memory/verification/rules.py`
- Create: `src/workflow_memory/verification/llm_judge.py`
- Create: `src/workflow_memory/optimization/optimizer.py`
- Create: `src/workflow_memory/retrieval/scoring.py`
- Create: `src/workflow_memory/retrieval/hints.py`
- Create: `src/workflow_memory/pipeline/baseline.py`
- Create: `src/workflow_memory/pipeline/optimize.py`
- Create: `src/workflow_memory/pipeline/memory_run.py`
- Create: `src/workflow_memory/eval/batch.py`
- Create: `src/workflow_memory/eval/reporting.py`

### Data And Task Suite Files

- Create: `tasks/recreation_gov.yaml`
- Create: `tasks/mai_schedule.yaml`
- Create: `artifacts/.gitkeep`
- Create: `data/.gitkeep`

### Tests

- Create: `tests/test_cli_smoke.py`
- Create: `tests/test_config.py`
- Create: `tests/test_storage.py`
- Create: `tests/test_adapters.py`
- Create: `tests/test_fingerprints.py`
- Create: `tests/test_loops.py`
- Create: `tests/test_verification.py`
- Create: `tests/test_optimization_pass.py`
- Create: `tests/test_browser_runner_contract.py`
- Create: `tests/test_llm_contracts.py`
- Create: `tests/test_retrieval.py`
- Create: `tests/test_admission.py`
- Create: `tests/test_eval_batch.py`

## Task 1: Bootstrap Project And Config Surface

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `config/project.yaml`
- Create: `src/workflow_memory/__init__.py`
- Create: `src/workflow_memory/cli.py`
- Test: `tests/test_cli_smoke.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_smoke.py
from typer.testing import CliRunner

from workflow_memory.cli import app


def test_cli_shows_expected_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "baseline" in result.stdout
    assert "optimize" in result.stdout
    assert "memory-run" in result.stdout
    assert "eval-batch" in result.stdout
```

```python
# tests/test_config.py
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
    assert config.admission.min_relative_improvement == 0.10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_smoke.py tests/test_config.py -v`
Expected: FAIL with import errors for `workflow_memory.cli` and `workflow_memory.config`

- [ ] **Step 3: Write the minimal implementation**

```toml
# pyproject.toml
[project]
name = "workflow-memory"
version = "0.1.0"
description = "Workflow memory layer for browser-use"
readme = "README.md"
requires-python = ">=3.11,<3.13"
dependencies = [
  "browser-use==0.12.6",
  "playwright",
  "typer>=0.15.3",
  "pydantic>=2.11.3",
  "PyYAML>=6.0.2",
  "rapidfuzz>=3.13.0",
  "openai>=1.76.0",
  "langchain-openai>=0.3.14",
  "python-dotenv>=1.0.1",
  "pytest>=8.3.5",
]

[project.scripts]
workflow-memory = "workflow_memory.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/workflow_memory/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/workflow_memory/config.py
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
    admission: AdmissionConfig
    retrieval: RetrievalConfig
    parallelism: ParallelismConfig


def load_config(path: Path) -> ProjectConfig:
    data = yaml.safe_load(path.read_text())
    return ProjectConfig.model_validate(data)
```

```python
# src/workflow_memory/cli.py
import typer

app = typer.Typer(help="Workflow memory CLI")


@app.command("baseline")
def baseline() -> None:
    """Run a baseline browser job."""


@app.command("optimize")
def optimize() -> None:
    """Run baseline, optimize, rerun, and admission."""


@app.command("memory-run")
def memory_run() -> None:
    """Run a task with admitted memory."""


@app.command("eval-batch")
def eval_batch() -> None:
    """Run an evaluation suite."""
```

```yaml
# config/project.yaml
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
```

```dotenv
# .env.example
OPENAI_API_KEY=your_openai_api_key
MAI_USERNAME=
MAI_PASSWORD=
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_smoke.py tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example config/project.yaml src/workflow_memory/__init__.py src/workflow_memory/config.py src/workflow_memory/cli.py tests/test_cli_smoke.py tests/test_config.py
git commit -m "feat: bootstrap workflow memory project"
```

## Task 2: Add Core Models, SQLite Schema, And Artifact Storage

**Files:**
- Create: `src/workflow_memory/models.py`
- Create: `src/workflow_memory/db.py`
- Create: `src/workflow_memory/storage/artifacts.py`
- Create: `src/workflow_memory/storage/repository.py`
- Create: `artifacts/.gitkeep`
- Create: `data/.gitkeep`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_storage.py
from pathlib import Path

from workflow_memory.db import initialize_db
from workflow_memory.models import RunArtifact
from workflow_memory.storage.artifacts import ArtifactStore
from workflow_memory.storage.repository import RunRepository


def test_run_repository_and_artifact_store_persist_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    artifacts_root = tmp_path / "artifacts"
    initialize_db(db_path)

    store = ArtifactStore(artifacts_root)
    repo = RunRepository(db_path)

    run = RunArtifact(
        run_id="run-001",
        site="recreation_gov",
        task_family="campground_search",
        run_mode="baseline",
        status="succeeded",
        task_input={"query": "Yosemite"},
        metrics={"action_count": 12},
    )

    paths = store.write_run_artifacts(run, {"trace": []}, {"normalized": []}, {"result": {}})
    repo.insert_run(run, paths)

    fetched = repo.get_run("run-001")
    assert fetched["site"] == "recreation_gov"
    assert Path(paths["trace"]).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_storage.py -v`
Expected: FAIL with missing imports for storage and db modules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/models.py
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
```

```python
# src/workflow_memory/db.py
import sqlite3
from pathlib import Path


def initialize_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              site TEXT NOT NULL,
              task_family TEXT NOT NULL,
              run_mode TEXT NOT NULL,
              status TEXT NOT NULL,
              task_input_json TEXT NOT NULL,
              metrics_json TEXT NOT NULL,
              trace_path TEXT NOT NULL,
              normalized_path TEXT NOT NULL,
              result_path TEXT NOT NULL
            )
            """
        )
        connection.commit()
```

```python
# src/workflow_memory/storage/artifacts.py
import json
from pathlib import Path
from typing import Any

from workflow_memory.models import RunArtifact


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write_run_artifacts(
        self,
        run: RunArtifact,
        trace_payload: dict[str, Any],
        normalized_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> dict[str, str]:
        run_dir = self.root / "runs" / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        trace_path = run_dir / "trace.json"
        normalized_path = run_dir / "normalized.json"
        result_path = run_dir / "result.json"
        trace_path.write_text(json.dumps(trace_payload, indent=2, ensure_ascii=False))
        normalized_path.write_text(json.dumps(normalized_payload, indent=2, ensure_ascii=False))
        result_path.write_text(json.dumps(result_payload, indent=2, ensure_ascii=False))
        return {
            "trace": str(trace_path),
            "normalized": str(normalized_path),
            "result": str(result_path),
        }
```

```python
# src/workflow_memory/storage/repository.py
import json
import sqlite3
from pathlib import Path
from typing import Any

from workflow_memory.models import RunArtifact


class RunRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def insert_run(self, run: RunArtifact, paths: dict[str, str]) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO runs (
                  run_id, site, task_family, run_mode, status,
                  task_input_json, metrics_json, trace_path, normalized_path, result_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.site,
                    run.task_family,
                    run.run_mode,
                    run.status,
                    json.dumps(run.task_input),
                    json.dumps(run.metrics),
                    paths["trace"],
                    paths["normalized"],
                    paths["result"],
                ),
            )
            connection.commit()

    def get_run(self, run_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT run_id, site, task_family, status, trace_path FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return {"run_id": row[0], "site": row[1], "task_family": row[2], "status": row[3], "trace_path": row[4]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/models.py src/workflow_memory/db.py src/workflow_memory/storage/artifacts.py src/workflow_memory/storage/repository.py artifacts/.gitkeep data/.gitkeep tests/test_storage.py
git commit -m "feat: add run storage and artifacts"
```

## Task 3: Define Site Adapter Contracts And Public Benchmark Suites

**Files:**
- Create: `src/workflow_memory/site_adapters/base.py`
- Create: `src/workflow_memory/site_adapters/recreation_gov.py`
- Create: `src/workflow_memory/site_adapters/mai_schedule.py`
- Create: `tasks/recreation_gov.yaml`
- Create: `tasks/mai_schedule.yaml`
- Test: `tests/test_adapters.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapters.py
from workflow_memory.site_adapters.mai_schedule import MaiScheduleAdapter
from workflow_memory.site_adapters.recreation_gov import RecreationGovAdapter


def test_recreation_adapter_builds_signature() -> None:
    adapter = RecreationGovAdapter()
    signature = adapter.build_task_signature(
        {
            "query": "Yosemite",
            "dates": "2026-06-10:2026-06-12",
            "equipment_type": "tent",
            "pet_policy": "allowed",
        }
    )
    assert signature["site"] == "recreation_gov"
    assert signature["task_family"] == "campground_search"


def test_mai_adapter_exposes_public_entrypoint() -> None:
    adapter = MaiScheduleAdapter()
    assert "groups.php" in adapter.entrypoint_url
    assert adapter.supports_auth is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_adapters.py -v`
Expected: FAIL with missing adapter modules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/site_adapters/base.py
from abc import ABC, abstractmethod
from typing import Any


class SiteAdapter(ABC):
    site_id: str
    task_family: str
    entrypoint_url: str
    supports_auth: bool = False

    @abstractmethod
    def build_task_signature(self, task_input: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_task_prompt(self, task_input: dict[str, Any]) -> str:
        raise NotImplementedError
```

```python
# src/workflow_memory/site_adapters/recreation_gov.py
from typing import Any

from workflow_memory.site_adapters.base import SiteAdapter


class RecreationGovAdapter(SiteAdapter):
    site_id = "recreation_gov"
    task_family = "campground_search"
    entrypoint_url = "https://www.recreation.gov/"

    def build_task_signature(self, task_input: dict[str, Any]) -> dict[str, Any]:
        return {
            "site": self.site_id,
            "task_family": self.task_family,
            "query": task_input["query"].strip().lower(),
            "equipment_type": task_input.get("equipment_type", "").strip().lower(),
            "pet_policy": task_input.get("pet_policy", "").strip().lower(),
        }

    def build_task_prompt(self, task_input: dict[str, Any]) -> str:
        return (
            "Find a campground or campsite on Recreation.gov using the supplied filters, "
            "open the most relevant result, and return a structured summary."
        )
```

```python
# src/workflow_memory/site_adapters/mai_schedule.py
from typing import Any

from workflow_memory.site_adapters.base import SiteAdapter


class MaiScheduleAdapter(SiteAdapter):
    site_id = "mai_schedule"
    task_family = "public_schedule_lookup"
    entrypoint_url = "https://mai.ru/education/studies/schedule/groups.php"
    supports_auth = False

    def build_task_signature(self, task_input: dict[str, Any]) -> dict[str, Any]:
        return {
            "site": self.site_id,
            "task_family": self.task_family,
            "group": task_input.get("group", "").strip().lower(),
            "week": task_input.get("week", "").strip().lower(),
            "day": task_input.get("day", "").strip().lower(),
        }

    def build_task_prompt(self, task_input: dict[str, Any]) -> str:
        return (
            "Open the public MAI schedule page, locate the schedule for the provided input, "
            "and return class time, subject, room, teacher, and date context."
        )
```

```yaml
# tasks/recreation_gov.yaml
site: recreation_gov
task_family: campground_search
cases:
  - case_id: rec-001
    input:
      query: Yosemite
      dates: "2026-06-10:2026-06-12"
      equipment_type: tent
      pet_policy: allowed
```

```yaml
# tasks/mai_schedule.yaml
site: mai_schedule
task_family: public_schedule_lookup
cases:
  - case_id: mai-001
    input:
      group: М3О-101Б-24
      week: current
      day: monday
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_adapters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/site_adapters/base.py src/workflow_memory/site_adapters/recreation_gov.py src/workflow_memory/site_adapters/mai_schedule.py tasks/recreation_gov.yaml tasks/mai_schedule.yaml tests/test_adapters.py
git commit -m "feat: add public benchmark site adapters"
```

## Task 4: Build Baseline Execution Core And Partial Artifact Handling

**Files:**
- Create: `src/workflow_memory/runtime/browser_runner.py`
- Create: `src/workflow_memory/runtime/sessions.py`
- Create: `src/workflow_memory/pipeline/baseline.py`
- Modify: `src/workflow_memory/models.py`
- Test: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_smoke.py
from workflow_memory.models import BaselineResult


def test_baseline_result_preserves_partial_failure_metadata() -> None:
    result = BaselineResult(
        run_id="run-002",
        status="failed_execution",
        failure_stage="browser_use",
        error_summary="timeout while waiting for selector",
        partial_artifacts_written=True,
        raw_output={},
        action_history=[],
    )
    assert result.status == "failed_execution"
    assert result.partial_artifacts_written is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_smoke.py -v`
Expected: FAIL because `BaselineResult` is undefined

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/models.py
from typing import Any

from pydantic import BaseModel, Field


class BaselineResult(BaseModel):
    run_id: str
    status: str
    failure_stage: str | None = None
    error_summary: str | None = None
    partial_artifacts_written: bool = False
    raw_output: dict[str, Any] = Field(default_factory=dict)
    action_history: list[dict[str, Any]] = Field(default_factory=list)


class RunArtifact(BaseModel):
    run_id: str
    site: str
    task_family: str
    run_mode: str
    status: str
    task_input: dict[str, Any]
    metrics: dict[str, Any] = Field(default_factory=dict)
```

```python
# src/workflow_memory/runtime/sessions.py
from pathlib import Path


def session_profile_dir(site: str, root: Path) -> Path:
    profile = root / site
    profile.mkdir(parents=True, exist_ok=True)
    return profile
```

```python
# src/workflow_memory/runtime/browser_runner.py
from typing import Any

from workflow_memory.models import BaselineResult


class BrowserUseRunner:
    def run(self, task_prompt: str, entrypoint_url: str) -> BaselineResult:
        return BaselineResult(
            run_id="stub-run",
            status="succeeded",
            raw_output={"entrypoint_url": entrypoint_url, "task_prompt": task_prompt},
            action_history=[],
            partial_artifacts_written=True,
        )

    def failed_run(self, error_summary: str) -> BaselineResult:
        return BaselineResult(
            run_id="failed-run",
            status="failed_execution",
            failure_stage="browser_use",
            error_summary=error_summary,
            partial_artifacts_written=True,
            raw_output={},
            action_history=[],
        )
```

```python
# src/workflow_memory/pipeline/baseline.py
from workflow_memory.models import BaselineResult
from workflow_memory.runtime.browser_runner import BrowserUseRunner
from workflow_memory.site_adapters.base import SiteAdapter


def run_baseline(adapter: SiteAdapter, task_input: dict[str, str]) -> BaselineResult:
    runner = BrowserUseRunner()
    return runner.run(adapter.build_task_prompt(task_input), adapter.entrypoint_url)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/models.py src/workflow_memory/runtime/sessions.py src/workflow_memory/runtime/browser_runner.py src/workflow_memory/pipeline/baseline.py tests/test_cli_smoke.py
git commit -m "feat: add baseline execution core and failure metadata"
```

## Task 5: Implement Normalization, Fingerprints, And Loop Detection

**Files:**
- Create: `src/workflow_memory/analysis/normalize.py`
- Create: `src/workflow_memory/analysis/fingerprints.py`
- Create: `src/workflow_memory/analysis/loops.py`
- Test: `tests/test_fingerprints.py`
- Test: `tests/test_loops.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fingerprints.py
from workflow_memory.analysis.fingerprints import page_state_similarity


def test_page_state_similarity_marks_near_identical_states() -> None:
    left = {"url": "https://example.com/groups", "title": "Schedule", "labels": ["Group", "Week", "Display"]}
    right = {"url": "https://example.com/groups?x=1", "title": "Schedule", "labels": ["Group", "Week", "Display"]}
    assert page_state_similarity(left, right) >= 0.8
```

```python
# tests/test_loops.py
from workflow_memory.analysis.loops import count_loop_events


def test_count_loop_events_detects_repeated_states() -> None:
    states = [
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
        {"fingerprint": "A", "action": "click"},
        {"fingerprint": "B", "action": "type"},
    ]
    assert count_loop_events(states) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fingerprints.py tests/test_loops.py -v`
Expected: FAIL with missing analysis modules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/analysis/fingerprints.py
from collections.abc import Sequence


def _normalize_path(url: str) -> str:
    return url.split("?")[0].rstrip("/")


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def page_state_similarity(left: dict, right: dict) -> float:
    path_score = 1.0 if _normalize_path(left["url"]) == _normalize_path(right["url"]) else 0.0
    title_score = 1.0 if left["title"] == right["title"] else 0.0
    label_score = _jaccard(set(left.get("labels", [])), set(right.get("labels", [])))
    return round((0.4 * path_score) + (0.2 * title_score) + (0.4 * label_score), 2)
```

```python
# src/workflow_memory/analysis/loops.py
def count_loop_events(state_events: list[dict]) -> int:
    seen_patterns: set[tuple[str, str, str, str]] = set()
    loops = 0
    for index in range(len(state_events) - 3):
        pattern = (
            state_events[index]["fingerprint"],
            state_events[index]["action"],
            state_events[index + 1]["fingerprint"],
            state_events[index + 1]["action"],
        )
        if pattern in seen_patterns:
            loops += 1
            break
        seen_patterns.add(pattern)
    return loops
```

```python
# src/workflow_memory/analysis/normalize.py
from typing import Any


def normalize_action_history(action_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in action_history:
        normalized.append(
            {
                "action": item.get("action", "unknown"),
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "labels": item.get("labels", []),
            }
        )
    return normalized
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_fingerprints.py tests/test_loops.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/analysis/fingerprints.py src/workflow_memory/analysis/loops.py src/workflow_memory/analysis/normalize.py tests/test_fingerprints.py tests/test_loops.py
git commit -m "feat: add page state fingerprinting and loop detection"
```

## Task 6: Add Verification Layer And Single Optimization Pass

**Files:**
- Create: `src/workflow_memory/verification/rules.py`
- Create: `src/workflow_memory/verification/llm_judge.py`
- Create: `src/workflow_memory/optimization/optimizer.py`
- Test: `tests/test_verification.py`
- Test: `tests/test_optimization_pass.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_verification.py
from workflow_memory.verification.rules import rule_based_verdict


def test_rule_based_verdict_accepts_required_fields() -> None:
    verdict = rule_based_verdict(
        required_fields=["subject", "room", "time"],
        structured_output={"subject": "Math", "room": "A-101", "time": "09:00"},
    )
    assert verdict["passed"] is True
```

```python
# tests/test_optimization_pass.py
from workflow_memory.optimization.optimizer import build_hint_packet


def test_build_hint_packet_contains_required_sections() -> None:
    packet = build_hint_packet(
        analysis={"wasted_steps": ["back navigation"]},
        optimized_workflow={
            "likely_path": ["open results", "apply filters", "open top card"],
            "page_hints": ["results page", "details page"],
            "success_cues": ["required fields visible"],
            "mismatch_signals": ["filters missing"],
        },
    )
    assert "likely_path" in packet
    assert "mismatch_signals" in packet
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_verification.py tests/test_optimization_pass.py -v`
Expected: FAIL with missing verification and optimization modules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/verification/rules.py
def rule_based_verdict(required_fields: list[str], structured_output: dict[str, str]) -> dict[str, object]:
    missing = [field for field in required_fields if not structured_output.get(field)]
    return {"passed": not missing, "missing_fields": missing}
```

```python
# src/workflow_memory/verification/llm_judge.py
from typing import Any


def build_llm_judge_payload(task_description: str, structured_output: dict[str, Any], action_history: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task_description": task_description,
        "structured_output": structured_output,
        "action_history": action_history,
        "mode": "webjudge-inspired",
    }
```

```python
# src/workflow_memory/optimization/optimizer.py
from typing import Any


def build_hint_packet(analysis: dict[str, Any], optimized_workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": optimized_workflow.get("goal", "Complete the task efficiently"),
        "analysis": analysis,
        "likely_path": optimized_workflow["likely_path"],
        "page_hints": optimized_workflow["page_hints"],
        "success_cues": optimized_workflow["success_cues"],
        "mismatch_signals": optimized_workflow["mismatch_signals"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_verification.py tests/test_optimization_pass.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/verification/rules.py src/workflow_memory/verification/llm_judge.py src/workflow_memory/optimization/optimizer.py tests/test_verification.py tests/test_optimization_pass.py
git commit -m "feat: add verification and optimization pass primitives"
```

## Task 7: Implement Retrieval Scoring, Admission Policy, And Memory Persistence

**Files:**
- Create: `src/workflow_memory/retrieval/scoring.py`
- Create: `src/workflow_memory/retrieval/hints.py`
- Create: `src/workflow_memory/pipeline/optimize.py`
- Test: `tests/test_retrieval.py`
- Test: `tests/test_admission.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_retrieval.py
from workflow_memory.retrieval.scoring import score_candidate


def test_score_candidate_uses_field_by_field_similarity() -> None:
    score = score_candidate(
        query_signature={"query": "yosemite", "equipment_type": "tent", "pet_policy": "allowed"},
        memory_signature={"query": "yosemite", "equipment_type": "tent", "pet_policy": "allowed"},
        weights={"categorical_weight": 0.5, "set_weight": 0.2, "numeric_weight": 0.2, "text_weight": 0.1},
    )
    assert score == 1.0
```

```python
# tests/test_admission.py
from workflow_memory.pipeline.optimize import should_admit_memory


def test_should_admit_memory_requires_metric_improvement() -> None:
    admitted = should_admit_memory(
        baseline_metrics={"action_count": 20, "elapsed_time": 100.0, "loop_count": 4},
        rerun_metrics={"action_count": 16, "elapsed_time": 98.0, "loop_count": 4},
        baseline_passed=True,
        rerun_passed=True,
        min_relative_improvement=0.10,
    )
    assert admitted is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_retrieval.py tests/test_admission.py -v`
Expected: FAIL with missing retrieval and optimize pipeline modules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/retrieval/scoring.py
from difflib import SequenceMatcher


def score_candidate(query_signature: dict, memory_signature: dict, weights: dict[str, float]) -> float:
    categorical = 1.0 if query_signature.get("equipment_type") == memory_signature.get("equipment_type") else 0.0
    text = SequenceMatcher(None, query_signature.get("query", ""), memory_signature.get("query", "")).ratio()
    pet = 1.0 if query_signature.get("pet_policy") == memory_signature.get("pet_policy") else 0.0
    numeric = 1.0
    score = (
        (weights["categorical_weight"] * categorical)
        + (weights["text_weight"] * text)
        + (weights["set_weight"] * pet)
        + (weights["numeric_weight"] * numeric)
    )
    return round(score, 2)
```

```python
# src/workflow_memory/retrieval/hints.py
def format_hint_packet(memory_entry: dict) -> dict:
    return {
        "goal": memory_entry["workflow_summary"],
        "likely_path": memory_entry["likely_path"],
        "page_hints": memory_entry["page_hints"],
        "success_cues": memory_entry["success_cues"],
        "mismatch_signals": memory_entry["mismatch_signals"],
    }
```

```python
# src/workflow_memory/pipeline/optimize.py
def _relative_improvement(baseline: float, rerun: float) -> float:
    if baseline <= 0:
        return 0.0
    return (baseline - rerun) / baseline


def should_admit_memory(
    baseline_metrics: dict,
    rerun_metrics: dict,
    baseline_passed: bool,
    rerun_passed: bool,
    min_relative_improvement: float,
) -> bool:
    if not rerun_passed:
        return False
    if baseline_passed and not rerun_passed:
        return False

    improvements = [
        _relative_improvement(baseline_metrics["action_count"], rerun_metrics["action_count"]),
        _relative_improvement(baseline_metrics["elapsed_time"], rerun_metrics["elapsed_time"]),
        _relative_improvement(baseline_metrics["loop_count"], rerun_metrics["loop_count"]),
    ]
    return any(value >= min_relative_improvement for value in improvements)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_retrieval.py tests/test_admission.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/retrieval/scoring.py src/workflow_memory/retrieval/hints.py src/workflow_memory/pipeline/optimize.py tests/test_retrieval.py tests/test_admission.py
git commit -m "feat: add retrieval scoring and admission policy"
```

## Task 8: Add Memory-Run Mode, Batch Evaluation, And Reporting

**Files:**
- Create: `src/workflow_memory/pipeline/memory_run.py`
- Create: `src/workflow_memory/eval/batch.py`
- Create: `src/workflow_memory/eval/reporting.py`
- Modify: `src/workflow_memory/cli.py`
- Test: `tests/test_eval_batch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_batch.py
from workflow_memory.eval.reporting import summarize_eval_metrics


def test_summarize_eval_metrics_reports_site_level_counts() -> None:
    summary = summarize_eval_metrics(
        [
            {"site": "recreation_gov", "status": "succeeded", "action_count": 10},
            {"site": "recreation_gov", "status": "succeeded", "action_count": 8},
            {"site": "mai_schedule", "status": "failed_verification", "action_count": 12},
        ]
    )
    assert summary["recreation_gov"]["total_runs"] == 2
    assert summary["mai_schedule"]["failures"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_eval_batch.py -v`
Expected: FAIL with missing eval modules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/workflow_memory/pipeline/memory_run.py
def prepare_memory_run(task_input: dict, memory_entry: dict) -> dict:
    return {
        "task_input": task_input,
        "hint_packet": {
            "goal": memory_entry["workflow_summary"],
            "likely_path": memory_entry["likely_path"],
            "page_hints": memory_entry["page_hints"],
            "success_cues": memory_entry["success_cues"],
            "mismatch_signals": memory_entry["mismatch_signals"],
        },
    }
```

```python
# src/workflow_memory/eval/batch.py
from concurrent.futures import ThreadPoolExecutor


def run_eval_jobs(jobs: list[dict], max_workers: int) -> list[dict]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(lambda job: job, jobs))
```

```python
# src/workflow_memory/eval/reporting.py
def summarize_eval_metrics(results: list[dict]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for row in results:
        site = row["site"]
        summary.setdefault(site, {"total_runs": 0, "failures": 0, "action_counts": []})
        summary[site]["total_runs"] += 1
        summary[site]["action_counts"].append(row["action_count"])
        if row["status"] != "succeeded":
            summary[site]["failures"] += 1
    return summary
```

```python
# src/workflow_memory/cli.py
import typer

app = typer.Typer(help="Workflow memory CLI")


@app.command("baseline")
def baseline(site: str, task_family: str, input_path: str) -> None:
    print(f"baseline:{site}:{task_family}:{input_path}")


@app.command("optimize")
def optimize(site: str, task_family: str, input_path: str) -> None:
    print(f"optimize:{site}:{task_family}:{input_path}")


@app.command("memory-run")
def memory_run(site: str, task_family: str, input_path: str) -> None:
    print(f"memory-run:{site}:{task_family}:{input_path}")


@app.command("eval-batch")
def eval_batch(suite: str) -> None:
    print(f"eval-batch:{suite}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_eval_batch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/pipeline/memory_run.py src/workflow_memory/eval/batch.py src/workflow_memory/eval/reporting.py src/workflow_memory/cli.py tests/test_eval_batch.py
git commit -m "feat: add memory-run and evaluation reporting"
```

## Task 9: Finalize README, Submission Fit, And Public Benchmark Smoke Workflow

**Files:**
- Create: `README.md`
- Modify: `config/project.yaml`
- Test: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_smoke.py
from pathlib import Path


def test_readme_declares_required_track_tag() -> None:
    content = Path("README.md").read_text()
    assert content.splitlines()[0] == "Track: C+D"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_smoke.py::test_readme_declares_required_track_tag -v`
Expected: FAIL because `README.md` is missing or has the wrong first line

- [ ] **Step 3: Write the minimal implementation**

````markdown
# README.md
Track: C+D

# Browser Workflow Memory

Research prototype for a workflow-memory layer on top of `browser-use`.

## Quickstart

```bash
uv sync
playwright install chromium
uv run workflow-memory baseline --site recreation_gov --task-family campground_search --input-path tasks/recreation_gov.yaml
```

## Public Benchmarks

- `Recreation.gov`
- public MAI schedule pages on `mai.ru`

## Core Modes

- `baseline`
- `optimize`
- `memory-run`
- `eval-batch`

## Tool Use

The intended agent interface is the CLI:

```bash
workflow-memory optimize --site recreation_gov --task-family campground_search --input-path tasks/recreation_gov.yaml
```
````

```yaml
# config/project.yaml
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
private_sites:
  my_mai:
    enabled: false
    auth_mode: session_reuse
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_smoke.py::test_readme_declares_required_track_tag -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md config/project.yaml tests/test_cli_smoke.py
git commit -m "docs: add submission-ready readme and benchmark defaults"
```

## Verification Matrix

Run these before claiming `v1` is complete:

- `uv run pytest -v`
- `uv run workflow-memory baseline --site recreation_gov --task-family campground_search --input-path tasks/recreation_gov.yaml`
- `uv run workflow-memory baseline --site mai_schedule --task-family public_schedule_lookup --input-path tasks/mai_schedule.yaml`
- `uv run workflow-memory optimize --site recreation_gov --task-family campground_search --input-path tasks/recreation_gov.yaml`
- `uv run workflow-memory eval-batch --suite tasks/recreation_gov.yaml`

Expected evidence:
- artifacts created under `artifacts/`
- SQLite database created under `data/workflow_memory.sqlite`
- at least one optimization summary under `artifacts/optimizations/`
- at least one site-level evaluation summary

## Task 10: Replace The Baseline Stub With Real browser-use Execution

**Files:**
- Modify: `src/workflow_memory/runtime/browser_runner.py`
- Modify: `src/workflow_memory/pipeline/baseline.py`
- Modify: `src/workflow_memory/runtime/sessions.py`
- Test: `tests/test_browser_runner_contract.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_browser_runner_contract.py
from workflow_memory.runtime.browser_runner import BrowserUseRunner


def test_browser_use_runner_exposes_live_run_method() -> None:
    runner = BrowserUseRunner(model_name="gpt-4.1-mini")
    assert runner.model_name == "gpt-4.1-mini"
    assert callable(runner.run_live)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_browser_runner_contract.py -v`
Expected: FAIL because `BrowserUseRunner` does not yet expose `model_name` and `run_live`

- [ ] **Step 3: Write the real integration**

```python
# src/workflow_memory/runtime/browser_runner.py
import asyncio
from typing import Any

from browser_use import Agent
from langchain_openai import ChatOpenAI

from workflow_memory.models import BaselineResult


class BrowserUseRunner:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    async def _run(self, task_prompt: str) -> BaselineResult:
        llm = ChatOpenAI(model=self.model_name, temperature=0)
        agent = Agent(task=task_prompt, llm=llm)
        history = await agent.run()
        final_result = history.final_result() if hasattr(history, "final_result") else {}
        action_history = history.model_actions() if hasattr(history, "model_actions") else []
        return BaselineResult(
            run_id="live-run",
            status="succeeded",
            raw_output={"final_result": final_result},
            action_history=action_history,
            partial_artifacts_written=True,
        )

    def run_live(self, task_prompt: str) -> BaselineResult:
        return asyncio.run(self._run(task_prompt))
```

```python
# src/workflow_memory/pipeline/baseline.py
from workflow_memory.config import ProjectConfig
from workflow_memory.models import BaselineResult
from workflow_memory.runtime.browser_runner import BrowserUseRunner
from workflow_memory.site_adapters.base import SiteAdapter


def run_baseline(adapter: SiteAdapter, task_input: dict[str, str], config: ProjectConfig) -> BaselineResult:
    runner = BrowserUseRunner(model_name=config.judge_model)
    return runner.run_live(adapter.build_task_prompt(task_input))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_browser_runner_contract.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/runtime/browser_runner.py src/workflow_memory/pipeline/baseline.py src/workflow_memory/runtime/sessions.py tests/test_browser_runner_contract.py
git commit -m "feat: integrate live browser-use baseline runner"
```

## Task 11: Replace LLM Stubs With OpenAI-Backed Judge And Optimization

**Files:**
- Modify: `src/workflow_memory/verification/llm_judge.py`
- Modify: `src/workflow_memory/optimization/optimizer.py`
- Modify: `src/workflow_memory/pipeline/optimize.py`
- Test: `tests/test_llm_contracts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_contracts.py
from workflow_memory.optimization.optimizer import OptimizationResponse


def test_optimization_response_requires_analysis_and_workflow() -> None:
    payload = OptimizationResponse(
        analysis={"wasted_steps": ["back navigation"]},
        optimized_workflow={"likely_path": ["step-1"], "page_hints": [], "success_cues": [], "mismatch_signals": []},
        human_summary="Removed one unnecessary branch.",
    )
    assert payload.analysis["wasted_steps"] == ["back navigation"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_llm_contracts.py -v`
Expected: FAIL because `OptimizationResponse` is undefined

- [ ] **Step 3: Write the real integration**

```python
# src/workflow_memory/optimization/optimizer.py
from typing import Any

from openai import OpenAI
from pydantic import BaseModel


class OptimizationResponse(BaseModel):
    analysis: dict[str, Any]
    optimized_workflow: dict[str, Any]
    human_summary: str


def run_optimization_pass(model_name: str, packet: dict[str, Any]) -> OptimizationResponse:
    client = OpenAI()
    response = client.responses.create(
        model=model_name,
        input=[
            {
                "role": "system",
                "content": "Return JSON with analysis, optimized_workflow, and human_summary.",
            },
            {"role": "user", "content": str(packet)},
        ],
    )
    return OptimizationResponse.model_validate_json(response.output_text)


def build_hint_packet(analysis: dict[str, Any], optimized_workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": optimized_workflow.get("goal", "Complete the task efficiently"),
        "analysis": analysis,
        "likely_path": optimized_workflow["likely_path"],
        "page_hints": optimized_workflow["page_hints"],
        "success_cues": optimized_workflow["success_cues"],
        "mismatch_signals": optimized_workflow["mismatch_signals"],
    }
```

```python
# src/workflow_memory/verification/llm_judge.py
from openai import OpenAI


def run_llm_judge(model_name: str, payload: dict) -> dict:
    client = OpenAI()
    response = client.responses.create(
        model=model_name,
        input=[
            {
                "role": "system",
                "content": "Return JSON with passed, rationale, and confidence for a web-task verdict.",
            },
            {"role": "user", "content": str(payload)},
        ],
    )
    return {"raw_text": response.output_text}
```

```python
# src/workflow_memory/pipeline/optimize.py
from workflow_memory.optimization.optimizer import run_optimization_pass


def run_optimization(model_name: str, packet: dict) -> dict:
    response = run_optimization_pass(model_name, packet)
    return {
        "analysis": response.analysis,
        "optimized_workflow": response.optimized_workflow,
        "human_summary": response.human_summary,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_llm_contracts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow_memory/verification/llm_judge.py src/workflow_memory/optimization/optimizer.py src/workflow_memory/pipeline/optimize.py tests/test_llm_contracts.py
git commit -m "feat: add live llm judge and optimization integrations"
```

## Post-V1 Development Queue

After the main implementation is stable:

1. Add private `my.mai.ru` exploratory adapter behind a config flag.
2. Add richer rule-based success checks for both public benchmarks.
3. Add richer retrieval scoring for date ranges and filter overlap.
4. Add screencast script, `REFLECTION.md`, and benchmark result snapshots.
5. Add cached judge and optimizer outputs for cheaper reruns.
6. Add side-by-side baseline versus memory HTML report export.

## Spec Coverage Check

- Bootstrap and CLI tool surface: Task 1 and Task 8
- Public benchmark site adapters: Task 3
- Baseline runtime and partial artifacts: Task 4
- Fingerprinting and loop detection: Task 5
- Hybrid verification: Task 6 and Task 11
- Single optimization pass and hint packet: Task 6 and Task 11
- Retrieval scoring and admission: Task 7
- Evaluation runner and reporting: Task 8
- Live browser-use runtime: Task 10
- Submission alignment and track tagging: Task 9
