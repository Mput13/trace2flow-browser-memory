---
name: trace2flow
description: Browser Workflow Memory (Trace2Flow). Use this skill to solve repetitive browser tasks more efficiently by utilizing site-specific navigation hints, page graphs, and past successful runs. Use when the user needs to perform browser actions like "Find the schedule for group X on mai.ru", "Search for books on books.toscrape.com", or any task that involves navigating complex websites where "workflow-memory" might have previous experience.
---

# Trace2Flow (Browser Workflow Memory)

Trace2Flow is a research prototype that adds a memory layer on top of browser-use. It allows agents to perform repetitive browser tasks on the same website faster by remembering the navigation path and reusing it.

## Quick Start

The core commands follow this cycle:
1. **`run`** (baseline): The agent solves a task from scratch.
2. **`optimize`**: Analyzes the baseline run and extracts "hints" (memories).
3. **`memory-run`**: Solves the task with memory hints, significantly reducing steps.

## Essential Commands

Always run commands from the project root: `/Users/a/MAI/sem2/trace2flow`.
Use the absolute path to the virtualenv python: `/Users/a/MAI/sem2/trace2flow/.venv/bin/python3`.

### 1. Execute a Baseline Task
Use this when you haven't seen a site before or want to establish a new baseline.
```bash
/Users/a/MAI/sem2/trace2flow/.venv/bin/python3 -m workflow_memory.cli run --task "Your browser task here" --output
```

### 2. Learn from a Run
After a successful `run`, optimize it to create memory:
```bash
/Users/a/MAI/sem2/trace2flow/.venv/bin/python3 -m workflow_memory.cli optimize --run-id <UUID_FROM_RUN>
```

### 3. Execute with Memory
Use this for repeating tasks on known sites. It's faster and more reliable.
```bash
/Users/a/MAI/sem2/trace2flow/.venv/bin/python3 -m workflow_memory.cli memory-run --task "Your task" --output
```

### 4. Run Evaluation Suites
To compare baseline vs memory performance:
```bash
/Users/a/MAI/sem2/trace2flow/.venv/bin/python3 -m workflow_memory.cli eval-batch --suite tasks/mai_schedule_eval.yaml --output
```

## Domain Specifics

- **MAI Schedule**: Use this for any requests related to MAI university schedules.
  - Task example: "Find schedule for group M8O-105BV-25 on mai.ru"
- **Web Scraping**: Excellent for navigating sites like `books.toscrape.com` or `quotes.toscrape.com`.

## Knowledge Retrieval

- **Site Graph**: Trace2Flow builds a graph of site pages. Each node stores URL patterns, purpose, and query parameters.
- **Hints**: Memory hints suggest direct URLs to bypass tedious navigation.

For more details on implementation, see [Architecture Reference](references/architecture.md).
