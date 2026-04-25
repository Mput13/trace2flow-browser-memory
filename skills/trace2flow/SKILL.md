---
name: trace2flow
description: Browser Workflow Memory (Trace2Flow). Use this skill to solve repetitive browser tasks more efficiently by utilizing site-specific navigation hints, page graphs, and past successful runs. Use when the user needs to perform browser actions like "Find the schedule for group X on mai.ru", "Search for books on books.toscrape.com", or any task that involves navigating complex websites where "workflow-memory" might have previous experience.
---

# Trace2Flow (Browser Workflow Memory)

Trace2Flow adds a memory layer on top of browser-use. It allows agents to perform repetitive browser tasks faster by remembering the navigation path.

## Core Cycle for Professional Use

Always use the project virtualenv: `/Users/a/MAI/sem2/trace2flow/.venv/bin/python3`.
Project Root: `/Users/a/MAI/sem2/trace2flow`

### 1. Execute a Task (Smart Mode)
Try running with memory first. If memory exists, it will be used automatically. If not, it falls back to common navigation.
```bash
cd /Users/a/MAI/sem2/trace2flow && ./.venv/bin/python3 src/workflow_memory/cli.py memory-run --task "Task description" --output
```

### 2. Baseline & Learn (When no memory exists)
If `memory-run` is slow or fails, establish a fresh baseline and optimize:
```bash
# Run baseline
cd /Users/a/MAI/sem2/trace2flow && ./.venv/bin/python3 src/workflow_memory/cli.py run --task "Task description" --output

# Optimize (using run_id from output)
./.venv/bin/python3 src/workflow_memory/cli.py optimize --run-id <UUID>
```

## Batch Processing (Evaluations)
To run a full test suite and compare Baseline vs Memory performance:
```bash
cd /Users/a/MAI/sem2/trace2flow && ./.venv/bin/python3 src/workflow_memory/cli.py eval-batch --suite tasks/mai_schedule_eval.yaml --output
```

## Demo Mode (For Visualization)
Use `--no-headless` to see the Chromium window during the run:
```bash
./.venv/bin/python3 src/workflow_memory/cli.py memory-run --task "..." --no-headless
```

## Internal Logic
- **SQLite DB**: Data lives in `data/workflow_memory.sqlite`.
- **Artifacts**: Each run is saved in `artifacts/runs/`.
- **Hints**: LLM generates `direct_url` (to skip UI) and `page_hints` (to identify success states).

For architecture details, see [references/architecture.md](references/architecture.md).
