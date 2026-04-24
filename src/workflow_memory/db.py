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
