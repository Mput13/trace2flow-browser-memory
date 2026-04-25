Track: C+D

# Browser Workflow Memory

Research prototype: a workflow-memory layer on top of [browser-use](https://github.com/browser-use/browser-use). Repeated browser tasks on the same site become faster after one successful run — the agent learns the navigation path and reuses it on the next run.

**Core claim:** repeated browser tasks on the same site should take fewer actions after one successful run.

See [docs/findings.md](docs/findings.md) for experiment results.

## Quickstart

```bash
# 1. Install dependencies (requires Python 3.11–3.12)
pip install uv
uv sync
.venv/bin/playwright install chromium

# 2. Set your LLM key (OpenRouter recommended; plain OpenAI also works)
export OPENROUTER_API_KEY=sk-or-...
# or: export OPENAI_API_KEY=sk-...

# 3. Run a task
workflow-memory run \
  --task "Go to http://books.toscrape.com and find all Mystery books"
```

Output:

```
run_id: <uuid>
status: succeeded
action_count: 8
elapsed_seconds: 47.3
```

## The Memory Cycle

```
run        →  optimize  →  memory-run
(baseline)    (LLM extracts     (agent gets
               site knowledge)   navigation hints)
```

1. **`run`** — agent solves the task from scratch, artifacts saved
2. **`optimize`** — LLM analyzes the run, extracts a reusable hint packet and site page graph, stores in SQLite
3. **`memory-run`** — same task again, agent receives hints: direct URL, site map, success cues

## Commands

| Command | Description |
|---|---|
| `run --task "..."` | Baseline run, no memory |
| `run --task "..." --site <tag>` | Baseline run with explicit site grouping |
| `optimize --run-id <id>` | Analyze a completed run, store memory |
| `memory-run --task "..."` | Run with memory hints if available |
| `eval-batch --suite <file.yaml>` | Full comparison: baseline → optimize → memory for each case |
| `eval-batch --suite <file.yaml> --output` | Same, JSON output |

## Agent Interface (Claude / Codex / OpenClaw)

The CLI is the intended agent interface — any orchestrator can call it via subprocess:

```bash
# Run a task, capture JSON
workflow-memory run \
  --task "Find the schedule for group М8О-105БВ-25 at https://mai.ru/education/studies/schedule/groups.php" \
  --output-json
```

JSON response:

```json
{
  "run_id": "069ec105-...",
  "status": "succeeded",
  "final_result": "...",
  "action_count": 16,
  "elapsed_seconds": 235.2
}
```

After a successful run, extract and store memory:

```bash
workflow-memory optimize --run-id 069ec105-...
```

Future runs on the same site automatically use stored memory:

```bash
workflow-memory memory-run \
  --task "Find the schedule for group М8О-106БВ-25 at https://mai.ru/education/studies/schedule/groups.php"
```

## Task Suite Format

Create a YAML file to run multiple tasks in one batch:

```yaml
site: books.toscrape.com
task_family: book_search
cases:
  - case_id: books-01
    task: "Go to http://books.toscrape.com and find all Mystery books"
  - case_id: books-02
    task: "Go to http://books.toscrape.com and find all Science Fiction books"
```

Run the full baseline-vs-memory comparison:

```bash
workflow-memory eval-batch --suite tasks/books_toscrape_eval.yaml --output
```

## Configuration

`config/project.yaml`:

```yaml
llm_provider: openrouter
llm_base_url: https://openrouter.ai/api/v1
llm_api_key_env: OPENROUTER_API_KEY
judge_model: google/gemini-3-flash-preview
optimize_model: qwen/qwen3.6-plus
sqlite_path: data/workflow_memory.sqlite
artifacts_root: artifacts
admission:
  min_relative_improvement: 0.10
retrieval:
  fuzzy_threshold: 0.75
```

Set `OPENROUTER_API_KEY` in the environment or in `.env`.

## Site Graph

The memory system builds a per-site page graph from observed runs. Each node stores:
- URL pattern (with `{param}` placeholders)
- What the page does and when to use it
- Query parameters and their meaning
- Confidence score (decays over 90 days, resets on confirmed visit)

This lets the agent navigate directly to relevant pages on repeat visits, even for tasks with different parameters (e.g., a different group on the same university schedule site).

## Project Structure

```
src/workflow_memory/
  cli.py              # Typer CLI entry point
  pipeline/
    baseline.py       # Single baseline run
    optimize.py       # Optimization pass + memory storage
    memory_run.py     # Memory-augmented run
  eval/
    batch.py          # Eval suite runner
    reporting.py      # Metrics summary
  storage/
    repository.py     # SQLite CRUD (runs, memories, site_pages)
  optimization/
    optimizer.py      # LLM-based hint extraction
  retrieval/
    scoring.py        # Fuzzy task matching
tasks/                # Task suite YAML files
results/              # Eval output JSON
docs/
  findings.md         # Experiment results
```

## Running Tests

```bash
python -m pytest tests/ -q
```

145 tests, no external dependencies required.
