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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
              memory_id TEXT PRIMARY KEY,
              site TEXT NOT NULL,
              task TEXT NOT NULL,
              task_family TEXT,
              hint_packet_json TEXT NOT NULL,
              source_run_id TEXT NOT NULL,
              admitted_at TEXT NOT NULL,
              action_count_baseline INTEGER,
              action_count_rerun INTEGER,
              improvement_pct REAL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS site_pages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              site TEXT NOT NULL,
              url_pattern TEXT NOT NULL,
              description TEXT NOT NULL,
              params_json TEXT NOT NULL DEFAULT '{}',
              last_seen TEXT NOT NULL,
              confidence REAL NOT NULL DEFAULT 1.0,
              UNIQUE(site, url_pattern)
            )
            """
        )
        connection.commit()
