import json
import sqlite3
from pathlib import Path
import shutil

from workflow_memory.db import initialize_db
from workflow_memory.models import ArtifactPaths, PersistedRunRecord, RunArtifact


class RunRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        initialize_db(self.db_path)

    def insert_run(self, run: RunArtifact, paths: ArtifactPaths) -> None:
        try:
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
        except sqlite3.IntegrityError:
            raise
        except sqlite3.Error:
            run_dir = Path(paths["trace"]).parent
            shutil.rmtree(run_dir, ignore_errors=True)
            raise

    def get_run(self, run_id: str) -> PersistedRunRecord | None:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT
                  run_id,
                  site,
                  task_family,
                  run_mode,
                  status,
                  task_input_json,
                  metrics_json,
                  trace_path,
                  normalized_path,
                  result_path
                FROM runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return PersistedRunRecord(
            run_id=row["run_id"],
            site=row["site"],
            task_family=row["task_family"],
            run_mode=row["run_mode"],
            status=row["status"],
            task_input=json.loads(row["task_input_json"]),
            metrics=json.loads(row["metrics_json"]),
            trace_path=row["trace_path"],
            normalized_path=row["normalized_path"],
            result_path=row["result_path"],
        )
