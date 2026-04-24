import json
import sqlite3
from pathlib import Path

from workflow_memory.models import PersistedRunRecord, RunArtifact
from workflow_memory.storage.artifacts import ArtifactStore
from workflow_memory.storage.repository import RunRepository


def test_run_repository_and_artifact_store_persist_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    artifacts_root = tmp_path / "artifacts"

    store = ArtifactStore(artifacts_root)
    repo = RunRepository(db_path)

    run = RunArtifact(
        run_id="run-001",
        site="recreation_gov",
        task_family="campground_search",
        run_mode="baseline",
        status="succeeded",
        task_input={"query": "Yosemite"},
        metrics={"action_count": 12},
    )

    paths = store.write_run_artifacts(
        run, {"trace": []}, {"normalized": []}, {"result": {}}
    )
    repo.insert_run(run, paths)

    fetched = repo.get_run("run-001")
    assert fetched is not None
    persisted: PersistedRunRecord = fetched
    assert persisted["run_id"] == "run-001"
    assert fetched["site"] == "recreation_gov"
    assert fetched["run_mode"] == "baseline"
    assert fetched["task_input"] == {"query": "Yosemite"}
    assert fetched["metrics"] == {"action_count": 12}
    assert Path(paths["trace"]).exists()
    assert json.loads(Path(paths["trace"]).read_text(encoding="utf-8")) == {"trace": []}
    assert fetched["normalized_path"] == paths["normalized"]
    assert fetched["result_path"] == paths["result"]


def test_run_repository_get_run_returns_none_for_missing_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    repo = RunRepository(db_path)

    assert repo.get_run("missing-run") is None


def test_insert_run_cleans_up_artifacts_when_db_insert_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    artifacts_root = tmp_path / "artifacts"
    store = ArtifactStore(artifacts_root)
    repo = RunRepository(db_path)

    run = RunArtifact(
        run_id="run-002",
        site="recreation_gov",
        task_family="campground_search",
        run_mode="baseline",
        status="failed",
        task_input={"query": "Yosemite"},
        metrics={},
    )
    paths = store.write_run_artifacts(
        run, {"trace": ["step"]}, {"normalized": []}, {"result": {}}
    )
    run_dir = Path(paths["trace"]).parent

    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE runs")
        connection.commit()

    try:
        repo.insert_run(run, paths)
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError("expected sqlite insert to fail")

    assert not run_dir.exists()


def test_duplicate_insert_keeps_existing_artifacts(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    store = ArtifactStore(artifacts_root)

    original_run = RunArtifact(
        run_id="run-003",
        site="recreation_gov",
        task_family="campground_search",
        run_mode="baseline",
        status="succeeded",
        task_input={"query": "Yosemite"},
        metrics={},
    )
    original_paths = store.write_run_artifacts(
        original_run, {"trace": ["original"]}, {"normalized": []}, {"result": {}}
    )
    original_run_dir = Path(original_paths["trace"]).parent

    try:
        store.write_run_artifacts(
            original_run, {"trace": ["duplicate"]}, {"normalized": []}, {"result": {}}
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected duplicate artifact write to fail")

    assert original_run_dir.exists()
    assert json.loads(Path(original_paths["trace"]).read_text(encoding="utf-8")) == {
        "trace": ["original"]
    }
