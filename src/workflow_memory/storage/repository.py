import datetime
import json
import math
import sqlite3
from pathlib import Path
import shutil

from workflow_memory.db import initialize_db
from workflow_memory.models import ArtifactPaths, PersistedRunRecord, RunArtifact


_DECAY_DAYS = 90
_CONFIDENCE_FLOOR = 0.6


def effective_confidence(base_confidence: float, last_seen_iso: str) -> float:
    """Compute current confidence applying time decay with a floor.

    Mismatch entries (base_confidence=0) are never raised by the floor.
    Healthy entries decay from base toward 0.6 over 90 days, then hold.
    """
    if base_confidence <= 0:
        return 0.0
    try:
        last_seen = datetime.datetime.fromisoformat(last_seen_iso.rstrip("Z"))
    except ValueError:
        return base_confidence
    days_elapsed = max(0, (datetime.datetime.utcnow() - last_seen).days)
    decay = (1.0 - _CONFIDENCE_FLOOR) * min(days_elapsed / _DECAY_DAYS, 1.0)
    return max(base_confidence - decay, _CONFIDENCE_FLOOR)


class RunRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        initialize_db(self.db_path)

    def insert_run(self, run: RunArtifact, paths: ArtifactPaths, artifact_dir: Path) -> None:
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
            shutil.rmtree(artifact_dir, ignore_errors=True)
            raise

    def insert_memory(
        self,
        memory_id: str,
        site: str,
        task: str,
        task_family: str | None,
        hint_packet_dict: dict,
        source_run_id: str,
        action_count_baseline: int | None = None,
    ) -> None:
        import datetime

        admitted_at = datetime.datetime.utcnow().isoformat() + "Z"
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO memories (
                  memory_id, site, task, task_family,
                  hint_packet_json, source_run_id, admitted_at,
                  action_count_baseline, action_count_rerun, improvement_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    memory_id,
                    site,
                    task,
                    task_family,
                    json.dumps(hint_packet_dict, ensure_ascii=False),
                    source_run_id,
                    admitted_at,
                    action_count_baseline,
                ),
            )
            connection.commit()

    def get_memories_for_site(self, site_key: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                  memory_id, site, task, task_family,
                  hint_packet_json, source_run_id, admitted_at,
                  action_count_baseline, action_count_rerun, improvement_pct
                FROM memories
                WHERE site = ?
                """,
                (site_key,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_site_page(
        self,
        site: str,
        url_pattern: str,
        description: str,
        params: dict,
    ) -> None:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO site_pages (site, url_pattern, description, params_json, last_seen, confidence)
                VALUES (?, ?, ?, ?, ?, 1.0)
                ON CONFLICT(site, url_pattern) DO UPDATE SET
                  description = excluded.description,
                  params_json = excluded.params_json,
                  last_seen   = excluded.last_seen,
                  confidence  = 1.0
                """,
                (site, url_pattern, description, json.dumps(params, ensure_ascii=False), now),
            )
            conn.commit()

    def confirm_site_page(self, site: str, url_pattern: str) -> None:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE site_pages SET confidence=1.0, last_seen=? WHERE site=? AND url_pattern=?",
                (now, site, url_pattern),
            )
            conn.commit()

    def mismatch_site_page(self, site: str, url_pattern: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE site_pages SET confidence=0.0 WHERE site=? AND url_pattern=?",
                (site, url_pattern),
            )
            conn.commit()

    def get_site_pages(self, site: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT url_pattern, description, params_json, last_seen, confidence FROM site_pages WHERE site=?",
                (site,),
            ).fetchall()
        result = []
        for row in rows:
            conf = effective_confidence(row["confidence"], row["last_seen"])
            result.append({
                "url_pattern": row["url_pattern"],
                "description": row["description"],
                "params": json.loads(row["params_json"]),
                "last_seen": row["last_seen"],
                "confidence": conf,
            })
        return result

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
