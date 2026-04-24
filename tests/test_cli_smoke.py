from typer.testing import CliRunner

from workflow_memory.cli import app


def test_cli_shows_expected_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "baseline" in result.stdout
    assert "optimize" in result.stdout
    assert "memory-run" in result.stdout
    assert "eval-batch" in result.stdout
