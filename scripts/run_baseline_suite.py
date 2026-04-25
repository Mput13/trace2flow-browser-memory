"""Thin wrapper to run a baseline task suite.

Equivalent to ``workflow-memory baseline-suite --suite <path>``, kept for
users who prefer invoking a plain Python script (e.g. from editors or CI
that does not have the installed entrypoint on PATH).

Usage:
    python scripts/run_baseline_suite.py tasks/mai_schedule.yaml
    python scripts/run_baseline_suite.py tasks/mai_schedule.yaml --max-steps 30
    python scripts/run_baseline_suite.py tasks/mai_schedule.yaml --config config/project.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable when run directly without installation.
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workflow_memory.cli import app  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: run_baseline_suite.py <suite_path> [--max-steps N] [--config path]",
            file=sys.stderr,
        )
        return 2
    args = ["baseline-suite", "--suite", argv[1]] + argv[2:]
    try:
        app(args=args, standalone_mode=False)
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
