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
        return {
            "run_id": row[0],
            "site": row[1],
            "task_family": row[2],
            "status": row[3],
            "trace_path": row[4],
        }
