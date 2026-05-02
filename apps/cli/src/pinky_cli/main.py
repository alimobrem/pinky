import typer

app = typer.Typer(name="pinky", help="Pinky CLI — multi-cluster operations")

tasks_app = typer.Typer(help="Manage tasks")
clusters_app = typer.Typer(help="Manage clusters")
definitions_app = typer.Typer(help="Manage definitions (scanners, tools, skills, policies)")

app.add_typer(tasks_app, name="tasks")
app.add_typer(clusters_app, name="clusters")
app.add_typer(definitions_app, name="definitions")


@tasks_app.command("list")
def tasks_list(
    status: str | None = typer.Option(None, help="Filter by status"),
    cluster: str | None = typer.Option(None, help="Filter by cluster ID"),
) -> None:
    """List work items."""
    typer.echo("TODO: implement tasks list")


@clusters_app.command("list")
def clusters_list() -> None:
    """List registered clusters."""
    typer.echo("TODO: implement clusters list")


@definitions_app.command("list")
def definitions_list(
    kind: str = typer.Option("all", help="Filter by kind (scanner, tool, skill, policy, pipeline)"),
) -> None:
    """List definitions."""
    typer.echo(f"TODO: implement definitions list (kind={kind})")


@definitions_app.command("create")
def definitions_create(
    file: str = typer.Argument(help="Path to definition markdown file"),
) -> None:
    """Create or update a definition from a markdown file."""
    typer.echo(f"TODO: implement definitions create from {file}")


if __name__ == "__main__":
    app()
