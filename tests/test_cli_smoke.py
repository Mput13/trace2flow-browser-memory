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


def test_cli_commands_fail_until_implemented() -> None:
    runner = CliRunner()

    for command_name in ["baseline", "optimize", "memory-run", "eval-batch"]:
        result = runner.invoke(app, [command_name])
        assert result.exit_code != 0
        assert "not implemented yet" in result.stdout.lower()
