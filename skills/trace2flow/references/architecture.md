# Trace2Flow Architecture & CLI Reference

## Core Concepts

### Run Lifecycle
1. **Baseline**: Generic `browser-use` agent navigation. Artifacts (traces) are saved to `artifacts/runs/<uuid>`.
2. **Optimization**: LLM (configured in `config/project.yaml`) reads the trace and `normalized.json`. It looks for:
   - Stabilized URL patterns.
   - Page purposes.
   - Successful actions leading to the result.
3. **Memory Storage**: SQLite database at `data/workflow_memory.sqlite`.
4. **Memory Retrieval**: When a new task matches a site pattern via fuzzy search, hints are injected into the agent's observation space.

## Advanced CLI Options

| Flag | Purpose |
|---|---|
| `--headless / --no-headless` | Control browser visibility. |
| `--max-steps <int>` | Set the budget for the agent (default 25). |
| `--config <path>` | Override default `project.yaml`. |
| `--site <tag>` | Explicitly tag a site (useful for normalization). |

## File Layout Summary

- `artifacts/`: Raw run records (JSONs, snapshots).
- `data/`: SQLite memory database.
- `src/workflow_memory/`: Core Python logic.
- `tasks/`: Evaluation suite definitions (YAML).
- `results/`: Cached results of batch evaluations.
