import typer

app = typer.Typer(help="Workflow memory CLI")


@app.command("baseline")
def baseline() -> None:
    """Run a baseline browser job."""


@app.command("optimize")
def optimize() -> None:
    """Run baseline, optimize, rerun, and admission."""


@app.command("memory-run")
def memory_run() -> None:
    """Run a task with admitted memory."""


@app.command("eval-batch")
def eval_batch() -> None:
    """Run an evaluation suite."""
