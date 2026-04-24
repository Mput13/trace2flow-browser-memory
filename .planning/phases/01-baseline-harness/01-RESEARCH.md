# Phase 1: Baseline Harness - Research

**Researched:** 2026-04-25
**Domain:** browser-use 0.12.6 agent invocation, run artifact tracing, CLI wiring, MAI schedule site
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Start with a single target site and a single repeated-task family for Phase 1.
- **D-02:** Choose a task family that is stable, repeatable, and easy to verify manually or semi-automatically.
- **D-03:** Optimize for a site where repeated navigation waste is visible; avoid open-web or highly dynamic targets in the first phase.
- **D-04:** Use a standalone Python prototype as the execution shell around the browser-use runtime.
- **D-05:** Keep browser execution logic and experiment orchestration separate so later failures can be attributed cleanly.
- **D-06:** Expose the baseline through a CLI-first entrypoint rather than building UI.
- **D-07:** Persist per-run artifacts from the start: task input, site identifier, final status, elapsed time, and action-level trace.
- **D-08:** Make the run artifact format stable enough that Phase 2 and Phase 3 can consume the same traces without migration.
- **D-09:** Include explicit markers for loops, retries, and fallback behavior when available from the runtime.
- **D-10:** A Phase 1 baseline is only acceptable if the same task can be rerun reproducibly on the chosen site.
- **D-11:** Success checks should prefer simple deterministic validation over subjective manual judgment where possible.

### Claude's Discretion

- Exact browser-use framework wrapper structure
- Concrete file/module layout
- Choice of config format, logging library, and trace serialization details

### Deferred Ideas (OUT OF SCOPE)

- Cross-site reuse and generalized UI memory — future work beyond this phase
- Workflow-memory schema, retrieval logic, and mismatch handling — Phase 2
- Comparative experiment automation and metrics reporting — Phase 3
- Final README/demo/reflection packaging — Phase 4
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TASK-01 | User can run a baseline browser workflow for a predefined repeated task on a specific site. | `workflow-memory baseline --site mai_schedule --task-family schedule_lookup --input '...'` wires through the implemented `baseline` CLI stub into a real `browser-use` Agent.run_sync() call with artifact capture. |
| TASK-02 | User can configure at least one target site and a small family of repeated tasks for that site. | `config/project.yaml` already holds site/model config. A `tasks/mai_schedule.yaml` file defines the task family inputs. A `SiteAdapter` pattern isolates site-specific logic. |
| TASK-03 | Each run records execution artifacts needed for comparison, including outcome and action-level trace data. | `ArtifactStore` + `RunRepository` are already implemented. The plan must wire `AgentHistoryList.model_dump()` into `trace.json`, compute metrics from history, and write `result.json` and `normalized.json`. |
</phase_requirements>

---

## Summary

Plan 01-01 is complete. The project has a working Python package (`workflow_memory`), a strict Pydantic config loader, a SQLite-backed `RunRepository`, an `ArtifactStore` writing `trace.json / normalized.json / result.json`, and a Typer CLI with four stub commands. All 10 tests pass. The next two plans (01-02 and 01-03) must wire the `baseline` CLI command into a real `browser-use` execution, capture the resulting `AgentHistoryList` into the storage layer, and validate that the same task runs reproducibly.

The browser-use 0.12.6 Agent API is straightforward: instantiate with a `task` string and a `ChatOpenAI` LLM, call `agent.run_sync(max_steps=N)`, and receive an `AgentHistoryList`. The history object exposes `.model_dump()` for serialisation, `.total_duration_seconds()` for elapsed time, `.number_of_steps()` for action count, and `.final_result()` / `.is_successful()` for outcome. Per-step metadata (timing, actions, page state) is embedded in each `AgentHistory` item.

The target site for Phase 1 is the **public MAI schedule page** (`https://mai.ru/education/studies/schedule/groups.php`) — verified HTTP 200. The task family is **schedule_lookup**: navigate to the public MAI schedule, find the timetable for a given student group, and extract the structured schedule for a given day. No authentication is required. The site's repeatable navigation waste (searching for the same group URL path on each run from scratch) is exactly the pattern the memory layer will later exploit.

**Primary recommendation:** Implement a thin `runtime/browser_runner.py` module that wraps the browser-use Agent, a `site_adapters/mai_schedule.py` that builds the task prompt and validates the output, and a `pipeline/baseline.py` that orchestrates the run, persists artifacts, and returns a summary dict. Wire `cli.py` `baseline` command to call this pipeline with parsed CLI arguments.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Plans |
|-----------|----------------|
| Research prototype, not production software | No need for retry loops, rate-limit backoff, or production error handling beyond basic exception capture. |
| Evaluation must include baseline vs memory comparison | Artifact format chosen now (trace.json / normalized.json / result.json) must be stable through Phase 3. No schema changes without migration. |
| Memory layer decoupled from browser runtime | `pipeline/baseline.py` must not import from any future `memory/` module. All coupling goes one direction: memory layer reads artifacts, not the other way around. |
| CLI-first, no UI | All user-facing surface is `workflow-memory <command>`. |
| GSD workflow enforcement | All code changes go through GSD plan execution. |

---

## Standard Stack

### Core (already installed — verified against venv)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| browser-use | 0.12.6 | Browser agent runtime — executes tasks in Chromium | [VERIFIED: pyproject.toml] |
| playwright | 1.58.0 | Chromium automation substrate for browser-use | [VERIFIED: .venv playwright --version] |
| openai | >=1.76.0 | LLM API (gpt-4.1-mini judge, gpt-4.1 optimize) | [VERIFIED: pyproject.toml] |
| typer | >=0.15.3 | CLI framework wrapping all entrypoints | [VERIFIED: pyproject.toml] |
| pydantic | >=2.11.3 | Data validation for config and models | [VERIFIED: pyproject.toml] |
| PyYAML | >=6.0.2 | Config and task suite file loading | [VERIFIED: pyproject.toml] |
| python-dotenv | >=1.0.1 | `.env` credential loading | [VERIFIED: pyproject.toml] |
| pytest | >=8.3.5 | Test runner | [VERIFIED: pyproject.toml] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | 3.11 built-in | Required by browser-use Agent.run() — Agent is async-native | Every browser run uses asyncio.run() or Agent.run_sync() |
| json (stdlib) | 3.11 built-in | Artifact serialization | trace.json, normalized.json, result.json |
| time (stdlib) | 3.11 built-in | Wall-clock timing for elapsed_time metric | Wrap agent.run_sync() with time.time() |
| uuid7str | from browser-use transitive dep | Stable run IDs (already used by browser-use internally) | Use for run_id generation |

### Installation

All packages are already in the venv. No `pip install` needed for plan 01-02. If chromium was not yet downloaded:

```bash
.venv/bin/playwright install chromium
```

[VERIFIED: chromium launches cleanly as of 2026-04-25]

---

## Architecture Patterns

### Recommended Project Structure (plan 01-02 scope)

```
src/workflow_memory/
├── cli.py                    # Typer app — wire baseline command (MODIFY)
├── config.py                 # ProjectConfig loader (DONE)
├── models.py                 # RunArtifact, ArtifactPaths, PersistedRunRecord (DONE)
├── db.py                     # initialize_db (DONE)
├── storage/
│   ├── artifacts.py          # ArtifactStore (DONE)
│   └── repository.py         # RunRepository (DONE)
├── runtime/
│   └── browser_runner.py     # BrowserRunner: wraps browser-use Agent (CREATE)
├── site_adapters/
│   ├── base.py               # SiteAdapter abstract base (CREATE)
│   └── mai_schedule.py       # MAI schedule adapter (CREATE)
└── pipeline/
    └── baseline.py           # run_baseline() orchestrator (CREATE)

tasks/
└── mai_schedule.yaml         # task family input suite (CREATE)
```

### Pattern 1: Agent Instantiation and Run

**What:** Wrap `browser-use` Agent creation and execution in a synchronous helper. browser-use exposes `agent.run_sync()` which calls `asyncio.run()` internally.

**When to use:** Every time the baseline pipeline executes a single browser task.

**Key API facts (VERIFIED: inspected agent/service.py in .venv):**

```python
# Source: .venv/lib/python3.11/site-packages/browser_use/agent/service.py lines 131-210
from browser_use import Agent, BrowserProfile, ChatOpenAI
from browser_use.agent.views import AgentHistoryList

llm = ChatOpenAI(model="gpt-4.1-mini")

agent = Agent(
    task="Find the Monday schedule for group M3O-210Б-23 on mai.ru",
    llm=llm,
    browser_profile=BrowserProfile(headless=True),
    sensitive_data={"MAI_USERNAME": "...", "MAI_PASSWORD": "..."},  # optional
    max_failures=3,
    use_judge=False,         # disable built-in judge for cost control
    generate_gif=False,
    save_conversation_path=None,
)

history: AgentHistoryList = agent.run_sync(max_steps=30)
```

**Critical note:** `browser_use.ChatOpenAI` is NOT `openai.ChatCompletion`. It is browser-use's own wrapper in `browser_use.llm.openai.chat`. Always import from `browser_use`. [VERIFIED: .venv/lib/python3.11/site-packages/browser_use/llm/openai/chat.py]

### Pattern 2: Extracting Trace Data from AgentHistoryList

**What:** `AgentHistoryList` is the complete run record returned by `agent.run_sync()`. It contains all per-step data needed for artifact capture.

**Key methods (VERIFIED: browser_use/agent/views.py):**

```python
# Elapsed time
elapsed_secs = history.total_duration_seconds()

# Action count
action_count = history.number_of_steps()

# Final answer text
final_text = history.final_result()        # str | None

# Success (agent self-reports)
agent_success = history.is_successful()    # bool | None

# Done flag
is_done = history.is_done()               # bool

# All action names in order
action_names = history.action_names()     # list[str]

# Full serializable dict for trace.json
trace_dict = history.model_dump()          # dict — JSON-serializable via json.dumps

# Error list per step
errors = history.errors()                  # list[str | None]
```

**Sensitive data is automatically masked** when `sensitive_data` is passed to Agent: `history.model_dump(sensitive_data=self.sensitive_data)` redacts credential values with `<secret>KEY</secret>`. Use this when writing trace.json if credentials appear in agent context.

### Pattern 3: Normalized Payload Construction

**What:** The `normalized.json` artifact is a project-specific compact summary of the run. It is not the raw `AgentHistoryList` — it is a structured packet suitable for Phase 2 memory analysis.

**Normalized payload fields (based on spec in design doc):**

```python
normalized_payload = {
    "run_id": run.run_id,
    "site": run.site,
    "task_family": run.task_family,
    "task_input": run.task_input,
    "run_mode": run.run_mode,
    "status": run.status,
    "elapsed_seconds": elapsed_secs,
    "action_count": action_count,
    "action_names": action_names,      # list[str]
    "final_result": final_text,        # str | None
    "agent_success": agent_success,    # bool | None
    "is_done": is_done,               # bool
    "errors": [e for e in errors if e],
    "urls_visited": history.urls(),   # list[str | None]
}
```

### Pattern 4: CLI Baseline Command Wiring

**What:** The existing `cli.py` `baseline` stub must be replaced with a real implementation that accepts `--site`, `--task-family`, and `--input` CLI arguments, builds a task input dict, and delegates to `pipeline.baseline.run_baseline()`.

**Pattern (based on typer docs and existing cli.py structure):**

```python
# Source: existing cli.py stub, typer>=0.15.3 API [ASSUMED: typer docs]
@app.command("baseline")
def baseline(
    site: str = typer.Option(..., "--site", help="Site identifier"),
    task_family: str = typer.Option(..., "--task-family", help="Task family"),
    input_json: str = typer.Option("{}", "--input", help="JSON task input"),
    config_path: Path = typer.Option(Path("config/project.yaml"), "--config"),
) -> None:
    """Run a baseline browser job."""
    import json
    task_input = json.loads(input_json)
    cfg = load_config(config_path)
    result = run_baseline(site=site, task_family=task_family,
                          task_input=task_input, config=cfg)
    typer.echo(f"run_id: {result['run_id']}")
    typer.echo(f"status: {result['status']}")
    typer.echo(f"action_count: {result['action_count']}")
    typer.echo(f"elapsed_seconds: {result['elapsed_seconds']:.1f}")
```

### Pattern 5: SiteAdapter Interface

**What:** A minimal protocol that isolates site-specific knowledge from the generic pipeline. Phase 2 will add memory retrieval to this same interface.

```python
# Source: docs/superpowers/specs/2026-04-25-browser-workflow-memory-design.md
from abc import ABC, abstractmethod
from typing import Any

class SiteAdapter(ABC):
    site_id: str
    supported_task_families: list[str]

    @abstractmethod
    def build_task_prompt(self, task_family: str, task_input: dict[str, Any]) -> str:
        """Convert task_input into a natural-language task string for the browser-use Agent."""
        ...

    @abstractmethod
    def verify_result(self, task_family: str, task_input: dict[str, Any],
                      final_result: str | None) -> bool:
        """Rule-based success check. Returns True if the result looks valid."""
        ...
```

### Anti-Patterns to Avoid

- **Importing from `openai` directly for the LLM:** browser-use uses its own `ChatOpenAI` wrapper. Using the raw `openai.AsyncOpenAI` bypasses browser-use's structured output and action parsing.
- **Running `asyncio.run()` inside an already-running event loop:** browser-use provides `agent.run_sync()` which handles this. Use `run_sync()` everywhere in the CLI pipeline.
- **Calling `ArtifactStore` and `RunRepository` in the wrong order:** always `store.write_run_artifacts()` first (returns paths), then `repo.insert_run(run, paths, artifact_dir=...)`. Reversing the order leaves the DB record pointing to non-existent files.
- **Constructing `run_id` from task inputs:** use `uuid7str()` for collision safety. Task inputs change per run; a UUID guarantees uniqueness even for identical inputs.
- **Blocking the browser agent on `use_judge=True` without a judge_llm budget:** the built-in judge makes an extra LLM call. Set `use_judge=False` for baseline runs to keep cost and latency predictable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser action execution | Custom Playwright loop | `browser_use.Agent.run_sync()` | browser-use handles DOM parsing, action selection, retry, LLM feedback loop. Building this from scratch would be weeks of work. |
| Trace serialization | Custom JSON serializer | `AgentHistoryList.model_dump()` | Already handles ActionResult, BrowserStateHistory, StepMetadata serialization with proper enum handling and sensitive data masking. |
| Action hash / loop detection | Custom loop counter | `browser_use.agent.views.ActionLoopDetector` (already in agent internals) | browser-use already tracks loop signals internally. Expose them via `AgentHistoryList.errors()` and normalized action counts. |
| Page fingerprinting | Custom DOM hash | `browser_use.agent.views.PageFingerprint.from_browser_state()` (in agent views) | Already computes URL + element_count + SHA-256(dom_text) fingerprint. Available if we access agent state directly; otherwise replicate the same hash at normalization time using URLs from `history.urls()`. |
| Run ID generation | timestamp-based IDs | `uuid_extensions.uuid7str()` | Monotonic UUIDs, already used throughout browser-use internals, safe for concurrent use. |
| Credential handling | Plaintext env var substitution | `Agent(sensitive_data={...})` | browser-use automatically redacts credential values from trace dumps. |

---

## Common Pitfalls

### Pitfall 1: `asyncio` Event Loop Conflicts

**What goes wrong:** Calling `asyncio.run(agent.run())` in a context that already has a running event loop (e.g., Jupyter, certain test fixtures) raises `RuntimeError: This event loop is already running`.

**Why it happens:** browser-use's `Agent.run()` is a coroutine. `asyncio.run()` creates a new event loop. Most test environments don't have this problem, but any async test fixture calling `await run_baseline()` could.

**How to avoid:** Always use `agent.run_sync(max_steps=N)` in synchronous CLI code. In async test code, call `await agent.run(max_steps=N)` directly. [VERIFIED: browser_use/agent/service.py line 4018]

### Pitfall 2: `sensitive_data` Warning on Missing `allowed_domains`

**What goes wrong:** When `sensitive_data` is passed to `Agent` but `BrowserProfile.allowed_domains` is not set, browser-use logs a loud security warning. This is not an error but generates confusing output.

**Why it happens:** browser-use warns that credentials could leak if the agent navigates to an unintended domain. [VERIFIED: browser_use/agent/service.py lines 526-571]

**How to avoid:** For the MAI schedule public benchmark (no credentials needed), do not pass `sensitive_data`. For `my.mai.ru` (future exploratory), set `BrowserProfile(allowed_domains=["my.mai.ru"])` when passing credentials.

### Pitfall 3: `BrowserProfile` Headless vs Display for Reproducibility

**What goes wrong:** `headless=False` requires a display. On headless CI or remote machines, `headless=False` causes browser launch failure.

**How to avoid:** Default to `headless=True` for all reproducibility runs. Allow override via config or CLI flag for local demo/screencast. The `project.yaml` should expose a `headless` knob.

### Pitfall 4: Missing Chromium Binaries

**What goes wrong:** `playwright.sync_api.Error: Executable doesn't exist at .../chromium_headless_shell-*` — the Playwright browser binary is not downloaded despite Playwright being installed as a Python package.

**Why it happens:** The Python package and the browser binary are separate. Installing the package does not download browsers.

**How to avoid:** Plan 01-02 must include a Wave 0 setup step that runs `playwright install chromium`. Include this in the one-command setup path. [VERIFIED: reproduced and resolved during research 2026-04-25]

### Pitfall 5: `AgentHistoryList.is_successful()` Returns None

**What goes wrong:** `history.is_successful()` returns `None` (not `False`) when the agent stopped before calling the `done` action. This happens when `max_steps` is exhausted or a hard failure occurs. Treating `None` as success is a bug.

**How to avoid:** Status logic must be: `"succeeded"` only if `is_done() and is_successful() is True`. Otherwise `"failed_execution"` if not done, `"failed_verification"` if done but `is_successful() is False`. [VERIFIED: browser_use/agent/views.py lines 741-748]

### Pitfall 6: `ArtifactStore.write_run_artifacts()` Raises `FileExistsError` on Duplicate `run_id`

**What goes wrong:** If `run_id` is derived from task inputs (not UUID), retrying the same task with the same input creates a collision and raises `FileExistsError` before even touching the DB.

**How to avoid:** Always generate `run_id` with `uuid7str()` — unique per invocation even with identical inputs. [VERIFIED: storage/artifacts.py line 21, `exist_ok=False`]

### Pitfall 7: MAI Schedule Page Dynamic Content

**What goes wrong:** `https://mai.ru/education/studies/schedule/groups.php` may load schedule data via JavaScript after the initial HTML response. The agent needs the JS to execute before it can read schedule entries.

**Why it happens:** Many university portals render schedule tables via XHR/fetch after page load.

**How to avoid:** browser-use waits for DOM stability automatically. For rule-based verification, check that `final_result()` contains schedule keywords (time format, subject name, room number) rather than checking for specific HTML elements. Observed during research: HTTP 200 on the groups page [VERIFIED: curl check 2026-04-25]; full JS execution behavior is [ASSUMED] to work under Playwright's default wait strategy.

---

## Code Examples

Verified patterns from source inspection:

### Minimal browser-use Agent run

```python
# Source: browser_use/agent/service.py — Agent.__init__ + run_sync
import time
from browser_use import Agent, BrowserProfile, ChatOpenAI
from browser_use.agent.views import AgentHistoryList

def run_agent_task(task_prompt: str, model: str, max_steps: int = 30) -> tuple[AgentHistoryList, float]:
    llm = ChatOpenAI(model=model)
    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser_profile=BrowserProfile(headless=True),
        use_judge=False,
        generate_gif=False,
        max_failures=3,
    )
    start = time.time()
    history = agent.run_sync(max_steps=max_steps)
    elapsed = time.time() - start
    return history, elapsed
```

### Deriving RunArtifact status from AgentHistoryList

```python
# Source: browser_use/agent/views.py lines 733-748
def derive_status(history: AgentHistoryList) -> str:
    if history.is_done() and history.is_successful() is True:
        return "succeeded"
    elif history.is_done() and history.is_successful() is False:
        return "failed_verification"
    else:
        return "failed_execution"
```

### Building trace payload for ArtifactStore

```python
# Source: browser_use/agent/views.py — AgentHistoryList.model_dump()
trace_payload = history.model_dump()          # full serializable dict
normalized_payload = {
    "run_id": run_id,
    "site": site,
    "task_family": task_family,
    "task_input": task_input,
    "run_mode": "baseline",
    "status": status,
    "elapsed_seconds": elapsed,
    "action_count": history.number_of_steps(),
    "action_names": history.action_names(),
    "final_result": history.final_result(),
    "agent_success": history.is_successful(),
    "is_done": history.is_done(),
    "errors": [e for e in history.errors() if e],
    "urls_visited": history.urls(),
}
result_payload = {
    "run_id": run_id,
    "status": status,
    "final_result": history.final_result(),
    "agent_success": history.is_successful(),
    "elapsed_seconds": elapsed,
    "action_count": history.number_of_steps(),
}
```

### MAI schedule task prompt pattern

```python
# Source: [ASSUMED] — based on design doc and public site URL
def build_mai_schedule_prompt(group: str, date: str) -> str:
    return (
        f"Go to https://mai.ru/education/studies/schedule/groups.php "
        f"and find the class schedule for student group '{group}' on {date}. "
        f"Extract the full list of classes for that day including: "
        f"time, subject name, class type, room number, and instructor name. "
        f"Return the result as a structured list."
    )
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `agent.run()` returned raw action list | `AgentHistoryList` with typed `AgentHistory` per step, each containing `model_output`, `result`, `state`, `metadata` | Rich structured trace available post-run without custom hooks |
| Separate `controller` parameter | `tools` parameter (controller is now an alias) | No behavior change; use `tools` for new code |
| `browser_use.Browser` | `browser_use.BrowserSession` (Browser is alias) | Use `BrowserSession` for new code; Browser alias still works in 0.12.6 |
| Raw `langchain_openai.ChatOpenAI` | `browser_use.ChatOpenAI` wrapper with structured output support | Must use `browser_use.ChatOpenAI`, not langchain version, for Action parsing |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MAI schedule page renders schedule data correctly under Playwright's default wait after page load (JS executes before agent reads content) | Common Pitfalls #7 | Agent may see incomplete DOM; rule-based verifier would report failure on first run. Mitigation: extend_system_message can include a "wait for page to fully load" hint. |
| A2 | `build_mai_schedule_prompt` structure (asking the agent to navigate to a specific URL) is a sufficient task prompt for browser-use to complete schedule lookup | Code Examples | Agent may fail to find schedule for the given group/date combination on first runs. Mitigation: run with debug logging and inspect trace.json. |
| A3 | typer `Option(...)` with `--task-family` (hyphen) maps correctly to `task_family` (underscore) parameter without explicit `click.option` alias in typer >=0.15.3 | Architecture Patterns #4 | CLI argument parsing fails. Mitigation: test CLI smoke test immediately after implementing. |

---

## Open Questions

1. **`tasks/mai_schedule.yaml` input schema**
   - What we know: task family is "schedule_lookup"; inputs are group identifier and date.
   - What's unclear: what is the exact format of MAI group identifiers (e.g., "М3О-210Б-23" or "M3O-210B-23" — Cyrillic vs Latin mix)?
   - Recommendation: inspect the public schedule page URL patterns to get canonical group IDs before writing the task suite. Use a small set (2-3 groups, 2-3 dates) that are stable enough for repeated runs.

2. **Rule-based verification for schedule lookup**
   - What we know: `SiteAdapter.verify_result()` should check for schedule-shaped output.
   - What's unclear: what minimal string pattern reliably indicates a valid schedule extraction? (time format? subject keyword?)
   - Recommendation: use a simple check: `final_result` is not None, has length > 50 characters, and contains at least one time-like pattern (`\d{1,2}:\d{2}`). This is sufficient for Phase 1 without LLM judging.

3. **Max steps budget for baseline runs**
   - What we know: `agent.run_sync(max_steps=N)` — the right N balances cost vs. giving the agent enough room to navigate.
   - What's unclear: how many steps does a typical MAI schedule lookup take without memory hints?
   - Recommendation: start with `max_steps=25` for Phase 1. Log `history.number_of_steps()` in every run artifact so this can be tuned in plan 01-03.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All runtime | Yes | 3.11.9 | — |
| browser-use 0.12.6 | Agent execution | Yes | 0.12.6 (pyproject.toml) | — |
| Playwright | Browser control | Yes | 1.58.0 | — |
| Chromium browser binary | Agent browser launch | Yes | installed 2026-04-25 | Run `playwright install chromium` |
| OpenAI API key | LLM calls (gpt-4.1-mini) | Requires .env | — | Provide via OPENAI_API_KEY |
| MAI public schedule page | Target site | Yes (HTTP 200) | — | — |
| SQLite | Run index | Yes (stdlib) | — | — |
| pytest | Tests | Yes | 9.0.3 | — |

**Missing dependencies with no fallback:**
- `OPENAI_API_KEY` — must be set in `.env` before any real browser run. Plan 01-02 tests should mock LLM calls or use a dry-run mode to avoid requiring the key in CI.

**Missing dependencies with fallback:**
- None remaining after chromium install.

---

## Sources

### Primary (HIGH confidence)
- `.venv/lib/python3.11/site-packages/browser_use/agent/service.py` — Agent constructor params, callbacks, `run_sync()`, sensitive_data handling
- `.venv/lib/python3.11/site-packages/browser_use/agent/views.py` — `AgentHistoryList`, `AgentHistory`, `ActionResult`, `StepMetadata`, `PageFingerprint`, loop detection
- `.venv/lib/python3.11/site-packages/browser_use/llm/openai/chat.py` — `ChatOpenAI` wrapper API
- `src/workflow_memory/storage/repository.py` — `RunRepository.insert_run()` signature
- `src/workflow_memory/storage/artifacts.py` — `ArtifactStore.write_run_artifacts()` contract
- `src/workflow_memory/models.py` — `RunArtifact`, `ArtifactPaths`, `PersistedRunRecord`
- `config/project.yaml` — live runtime config
- `curl https://mai.ru/education/studies/schedule/groups.php` — HTTP 200 confirmed 2026-04-25

### Secondary (MEDIUM confidence)
- `docs/superpowers/specs/2026-04-25-browser-workflow-memory-design.md` — architecture spec, artifact layout, site adapter interface pattern
- `.planning/phases/01-baseline-harness/01-CONTEXT.md` — locked decisions
- `.planning/phases/02-workflow-memory-layer/02-01-PLAN.md` + `02-01-SUMMARY.md` — confirmed storage boundary decisions

### Tertiary (LOW confidence)
- A3 (typer CLI argument mapping) — assumed from typer docs pattern; needs smoke test verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in .venv, versions confirmed
- Architecture patterns: HIGH — all API signatures verified against installed source
- Pitfalls: HIGH (5/7 verified) / LOW (2/7 assumed: JS rendering behavior, typer option naming)
- Environment: HIGH — all tools verified by running them

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (browser-use 0.12.6 is pinned; no upstream drift risk)
