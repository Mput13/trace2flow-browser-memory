# Phase 1 Baseline Runbook

Operator guide for running the Phase 1 baseline harness. Assumes plan 01-01 and
plan 01-02 are complete and `.venv/` is populated via `pip install -e .`.

## Setup

1. Install Chromium once (separate from the Python package):
   ```
   .venv/bin/playwright install chromium
   ```
2. Populate `.env` from `.env.example`. At minimum set `OPENAI_API_KEY`. The
   MAI schedule public page used in Phase 1 does NOT require `MAI_USERNAME` /
   `MAI_PASSWORD`.
3. Confirm config loads:
   ```
   .venv/bin/python -c "from workflow_memory.config import load_config; from pathlib import Path; print(load_config(Path('config/project.yaml')))"
   ```

## Run a single task

Quick form (copy-paste):
```
.venv/bin/workflow-memory baseline --site mai_schedule --task-family schedule_lookup --input '{"group":"М3О-210Б-23","date":"2026-04-27"}' --config config/project.yaml
```

Multi-line form for readability:
```
.venv/bin/workflow-memory baseline \
    --site mai_schedule \
    --task-family schedule_lookup \
    --input '{"group":"М3О-210Б-23","date":"2026-04-27"}' \
    --config config/project.yaml
```

The command prints `run_id`, `status`, `action_count`, `elapsed_seconds`.
Artifacts land under `artifacts/runs/<run_id>/` and a row is inserted into
`data/workflow_memory.sqlite` (path controlled by `config/project.yaml`).

## Run the full suite

Quick form (copy-paste):
```
.venv/bin/workflow-memory baseline-suite --suite tasks/mai_schedule.yaml --config config/project.yaml
```

Multi-line form for readability:
```
.venv/bin/workflow-memory baseline-suite \
    --suite tasks/mai_schedule.yaml \
    --config config/project.yaml
```

Or via the helper script:

```
.venv/bin/python scripts/run_baseline_suite.py tasks/mai_schedule.yaml
```

Each input in the suite produces one run. The command prints a per-run line
and a final `Suite complete: total=N succeeded=X failed=Y` summary.

## Inspect artifacts

Each run directory (`artifacts/runs/<run_id>/`) contains three files:

- `trace.json` — full `AgentHistoryList.model_dump()` output from browser-use.
  Contains per-step actions, browser state snippets, LLM messages. Large.
- `normalized.json` — compact project-specific summary. THE stable schema
  Phase 2 and Phase 3 consume. Keys:

  | Key | Type | Description |
  |-----|------|-------------|
  | `run_id` | str | UUIDv7 string uniquely identifying this run |
  | `site` | str | e.g. `"mai_schedule"` |
  | `task_family` | str | e.g. `"schedule_lookup"` |
  | `task_input` | dict | Whatever was passed on `--input` |
  | `run_mode` | str | `"baseline"` in Phase 1 |
  | `status` | str | `"succeeded"` / `"failed_verification"` / `"failed_execution"` |
  | `elapsed_seconds` | float | Wall clock seconds for agent.run_sync |
  | `action_count` | int | Number of agent steps taken |
  | `action_names` | list[str] | Ordered action names from agent history |
  | `final_result` | str \| null | `history.final_result()` from browser-use |
  | `agent_success` | bool \| null | `history.is_successful()` from browser-use |
  | `is_done` | bool | `history.is_done()` from browser-use |
  | `errors` | list[str] | Non-null per-step error strings |
  | `urls_visited` | list[str \| null] | `history.urls()` — pages visited |

- `result.json` — human-readable summary (`run_id`, `status`, `final_result`,
  `agent_success`, `elapsed_seconds`, `action_count`, optional `error`).

Inspect a specific run:
```
cat artifacts/runs/<run_id>/result.json
jq . artifacts/runs/<run_id>/normalized.json
```

List runs via SQLite:
```
sqlite3 data/workflow_memory.sqlite \
    "SELECT run_id, site, task_family, status, json_extract(metrics_json,'$.elapsed_seconds') FROM runs ORDER BY rowid DESC LIMIT 20;"
```

## Reproducibility check

Run the same task twice and confirm:

1. Two distinct `run_id`s are produced.
2. Two separate artifact directories exist.
3. Both pass schema validation:
   ```
   .venv/bin/python scripts/check_artifact_schema.py artifacts
   ```
   Expected: every run printed with `OK`, process exit code 0.
4. `status` is `"succeeded"` for at least one run (MAI schedule page depends
   on site availability and agent navigation luck; one retry is acceptable
   for Phase 1 per the research-prototype framing).

If `status` is `"failed_execution"` on every attempt, inspect `trace.json`
via `jq '.history[-1]' artifacts/runs/<run_id>/trace.json` to diagnose.
Common causes:

- Chromium not installed — run `playwright install chromium`.
- `OPENAI_API_KEY` not set or invalid — re-check `.env`.
- MAI site temporarily unreachable — retry later.
- `max_steps=25` too low for this group/date — try `--max-steps 35`.

## Honest known limitations (Phase 1)

- Verifier is rule-based (length > 50 chars + one `\d{1,2}:\d{2}` pattern).
  It can both false-positive on non-schedule pages that happen to contain
  times and false-negative on very compact schedule outputs. Refinement is
  deferred to Phase 3 evaluation.
- No retry-on-failure. If the agent hits `max_steps`, the run is recorded as
  `failed_execution` and the operator decides whether to rerun.
- Cost per run is unbounded by the harness; it is bounded indirectly by
  `max_steps` and by browser-use's own LLM call pattern. Monitor OpenAI
  usage when running the full suite.
