from typer.testing import CliRunner

from workflow_memory.cli import app


def test_cli_shows_expected_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "optimize" in result.stdout
    assert "memory-run" in result.stdout
    assert "eval-batch" in result.stdout


def test_eval_batch_requires_suite_option() -> None:
    """eval-batch is implemented and requires --suite; invoking without it exits non-zero."""
    runner = CliRunner()
    result = runner.invoke(app, ["eval-batch"])
    assert result.exit_code != 0


def test_memory_run_requires_task_option() -> None:
    """memory-run without --task must exit non-zero (now implemented)."""
    runner = CliRunner()
    result = runner.invoke(app, ["memory-run"])
    assert result.exit_code != 0


def test_optimize_help_shows_run_id_option() -> None:
    """optimize command should be implemented and show --run-id option."""
    runner = CliRunner()
    result = runner.invoke(app, ["optimize", "--help"])
    assert result.exit_code == 0
    assert "--run-id" in result.stdout
