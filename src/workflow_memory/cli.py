import typer

app = typer.Typer(help="Workflow memory CLI")


def _not_implemented(command_name: str) -> None:
    typer.echo(f"{command_name} is not implemented yet.")
    raise typer.Exit(code=1)


@app.command("baseline")
def baseline() -> None:
    """Run a baseline browser job."""
    _not_implemented("baseline")


@app.command("optimize")
def optimize() -> None:
    """Run baseline, optimize, rerun, and admission."""
    _not_implemented("optimize")


@app.command("memory-run")
def memory_run() -> None:
    """Run a task with admitted memory."""
    _not_implemented("memory-run")


@app.command("eval-batch")
def eval_batch() -> None:
    """Run an evaluation suite."""
    _not_implemented("eval-batch")
