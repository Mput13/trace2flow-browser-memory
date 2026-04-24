from pathlib import Path

from workflow_memory.db import initialize_db
from workflow_memory.models import RunArtifact
from workflow_memory.storage.artifacts import ArtifactStore
from workflow_memory.storage.repository import RunRepository


def test_run_repository_and_artifact_store_persist_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_memory.sqlite"
    artifacts_root = tmp_path / "artifacts"
    initialize_db(db_path)

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
    assert fetched["site"] == "recreation_gov"
    assert Path(paths["trace"]).exists()
