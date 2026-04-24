import json
from pathlib import Path
from typing import Any

from workflow_memory.models import ArtifactPaths, RunArtifact


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write_run_artifacts(
        self,
        run: RunArtifact,
        trace_payload: dict[str, Any],
        normalized_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> ArtifactPaths:
        run_dir = self.root / "runs" / run.run_id
        if run_dir.exists():
            raise FileExistsError(f"artifact directory already exists for run_id={run.run_id}")
        run_dir.mkdir(parents=True, exist_ok=True)
        trace_path = run_dir / "trace.json"
        normalized_path = run_dir / "normalized.json"
        result_path = run_dir / "result.json"
        trace_path.write_text(
            json.dumps(trace_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        normalized_path.write_text(
            json.dumps(normalized_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        result_path.write_text(
            json.dumps(result_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return ArtifactPaths(
            trace=str(trace_path),
            normalized=str(normalized_path),
            result=str(result_path),
        )
