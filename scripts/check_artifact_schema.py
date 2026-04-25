"""Standalone validator for run artifact directories.

Usage:
    python scripts/check_artifact_schema.py <path>

<path> may be either:
  - a single run directory (contains trace.json / normalized.json / result.json)
  - an artifacts root (contains a "runs/" subdirectory of run directories)

Exits 0 if all directories validate, non-zero otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {"succeeded", "failed_verification", "failed_execution"}

NORMALIZED_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "run_id": str,
    "site": str,
    "task_family": str,
    "task_input": dict,
    "run_mode": str,
    "status": str,
    "elapsed_seconds": (int, float),
    "action_count": int,
    "action_names": list,
    "final_result": (str, type(None)),
    "agent_success": (bool, type(None)),
    "is_done": bool,
    "errors": list,
    "urls_visited": list,
}

RESULT_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "run_id": str,
    "status": str,
    "final_result": (str, type(None)),
    "agent_success": (bool, type(None)),
    "elapsed_seconds": (int, float),
    "action_count": int,
}


def _check_keys(
    name: str,
    payload: dict[str, Any],
    required: dict[str, type | tuple[type, ...]],
) -> list[str]:
    errors: list[str] = []
    for key, expected_type in required.items():
        if key not in payload:
            errors.append(f"{name}: missing key {key!r}")
            continue
        value = payload[key]
        if not isinstance(value, expected_type):
            errors.append(
                f"{name}: key {key!r} has type {type(value).__name__}, "
                f"expected {expected_type}"
            )
    status = payload.get("status")
    if isinstance(status, str) and status not in ALLOWED_STATUSES:
        errors.append(
            f"{name}: status {status!r} not in allowed {sorted(ALLOWED_STATUSES)}"
        )
    return errors


def check_artifact_dir(run_dir: Path) -> tuple[bool, list[str]]:
    """Validate a single run artifact directory.

    Args:
        run_dir: Path to a run directory containing trace.json,
                 normalized.json, and result.json.

    Returns:
        A ``(ok, errors)`` tuple.  ``ok`` is True when all checks pass;
        ``errors`` is a list of human-readable error strings.
    """
    errors: list[str] = []
    trace_path = run_dir / "trace.json"
    normalized_path = run_dir / "normalized.json"
    result_path = run_dir / "result.json"

    for p in (trace_path, normalized_path, result_path):
        if not p.is_file():
            errors.append(f"missing file: {p.name}")

    if errors:
        return False, errors

    # trace.json: we only validate that it is valid JSON (schema is
    # AgentHistoryList-defined upstream).
    try:
        json.loads(trace_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"trace.json: invalid JSON: {exc}")

    try:
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"normalized.json: invalid JSON: {exc}")
        normalized = None

    try:
        result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"result.json: invalid JSON: {exc}")
        result_payload = None

    if isinstance(normalized, dict):
        errors.extend(_check_keys("normalized.json", normalized, NORMALIZED_REQUIRED))
    if isinstance(result_payload, dict):
        errors.extend(_check_keys("result.json", result_payload, RESULT_REQUIRED))

    return len(errors) == 0, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: check_artifact_schema.py <run_dir_or_artifacts_root>",
            file=sys.stderr,
        )
        return 2
    target = Path(argv[1])
    if not target.exists():
        print(f"path does not exist: {target}", file=sys.stderr)
        return 2

    if (target / "trace.json").is_file():
        # target is a single run directory
        dirs = [target]
    elif (target / "runs").is_dir():
        # target is an artifacts root
        dirs = sorted(p for p in (target / "runs").iterdir() if p.is_dir())
    else:
        print(f"not a run dir or artifacts root: {target}", file=sys.stderr)
        return 2

    if not dirs:
        print(f"no run directories found under {target}", file=sys.stderr)
        return 2

    total_bad = 0
    for d in dirs:
        ok, errors = check_artifact_dir(d)
        if ok:
            print(f"OK  {d}")
        else:
            total_bad += 1
            print(f"BAD {d}")
            for err in errors:
                print(f"    - {err}", file=sys.stderr)
    if total_bad:
        print(f"{total_bad} run(s) failed schema check", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
