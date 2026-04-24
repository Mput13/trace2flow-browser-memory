---
phase: "02"
plan: "02-01"
subsystem: storage
tags: [schema, persistence, sqlite, artifacts]
key-files:
  created:
    - src/workflow_memory/models.py
    - src/workflow_memory/db.py
    - src/workflow_memory/storage/__init__.py
    - src/workflow_memory/storage/artifacts.py
    - src/workflow_memory/storage/repository.py
    - tests/test_storage.py
decisions:
  - RunArtifact is the canonical run record; ArtifactPaths is the filesystem contract
  - ArtifactStore owns all filesystem path derivation; RunRepository must not infer paths
  - SQLite runs table is the retrieval index; JSON files are the artifact blobs
  - Duplicate run_id is a hard error (IntegrityError), not a silent overwrite
  - Rollback on partial failure: ArtifactStore removes run dir; RunRepository removes run dir via caller-supplied artifact_dir
metrics:
  completed: 2026-04-25
---

# Plan 02-01: Memory Schema and Persistence Boundary — Summary

**One-liner:** Established the full storage layer — RunArtifact model, ArtifactStore (filesystem), RunRepository (SQLite) — with clean separation of concerns and 5/5 tests green.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | Define run models and DB schema | src/workflow_memory/models.py, src/workflow_memory/db.py |
| 2 | Implement ArtifactStore and RunRepository with storage contracts | src/workflow_memory/storage/artifacts.py, src/workflow_memory/storage/repository.py, tests/test_storage.py |

## Changes Made

### src/workflow_memory/models.py
- `RunArtifact` — Pydantic model: `run_id`, `site`, `task_family`, `run_mode`, `status`, `task_input`, `metrics`
- `ArtifactPaths` — TypedDict: `trace`, `normalized`, `result` (string paths)
- `PersistedRunRecord` — TypedDict: full round-trip record from SQLite

### src/workflow_memory/db.py
- `initialize_db(path: Path)` — creates `runs` table with all required columns; idempotent (`CREATE TABLE IF NOT EXISTS`)

### src/workflow_memory/storage/artifacts.py
- `ArtifactStore(root: Path)` — writes `trace.json`, `normalized.json`, `result.json` into `root/runs/{run_id}/`
- Atomic: on any write error, removes the run directory and re-raises
- On duplicate `run_id`: raises `FileExistsError` (directory already exists)

### src/workflow_memory/storage/repository.py
- `RunRepository(db_path: Path)` — calls `initialize_db` on construction
- `insert_run(run, paths, artifact_dir)` — INSERT to SQLite; on `sqlite3.Error` removes `artifact_dir` and re-raises; on `IntegrityError` re-raises without cleanup
- `get_run(run_id)` — SELECT by run_id, returns `PersistedRunRecord | None`
- Boundary fix applied: `artifact_dir` is passed by caller, not inferred from paths

## Test Results

```
tests/test_storage.py::test_run_repository_and_artifact_store_persist_run              PASSED
tests/test_storage.py::test_run_repository_get_run_returns_none_for_missing_run        PASSED
tests/test_storage.py::test_insert_run_cleans_up_artifacts_when_db_insert_fails        PASSED
tests/test_storage.py::test_duplicate_insert_keeps_existing_artifacts                  PASSED
tests/test_storage.py::test_failed_artifact_write_rolls_back_run_directory             PASSED

5 passed in 0.03s
```

## Deviations from Plan

- `artifact_dir` boundary fix applied post-implementation via quick task 260425-24c (minor refactor, no semantic change).
