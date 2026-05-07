"""Pinky CLI — operator automation interface wrapping the REST API."""

import json
import os

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="pinky", help="Pinky CLI — multi-cluster operations")
console = Console()

API_URL = os.environ.get("PINKY_API_URL", "http://localhost:8000")


def _get(path: str, params: dict | None = None) -> dict:
    try:
        r = httpx.get(f"{API_URL}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error {e.response.status_code}:[/red] {e.response.text}")
        raise typer.Exit(1) from None
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to {API_URL}[/red]")
        raise typer.Exit(1) from None


def _post(path: str, data: dict | None = None) -> dict:
    try:
        r = httpx.post(f"{API_URL}{path}", json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error {e.response.status_code}:[/red] {e.response.text}")
        raise typer.Exit(1) from None


# --- Tasks ---

tasks_app = typer.Typer(help="Manage tasks")
app.add_typer(tasks_app, name="tasks")


@tasks_app.command("list")
def tasks_list(
    status: str | None = typer.Option(None, help="Filter by status"),
    cluster: str | None = typer.Option(None, help="Filter by cluster ID"),
) -> None:
    """List work items."""
    params = {}
    if status:
        params["status"] = status
    if cluster:
        params["cluster_id"] = cluster

    data = _get("/api/v1/work-items", params)
    table = Table(title="Tasks")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Confidence")

    for item in data["items"]:
        conf = f"{int(item['confidence'] * 100)}%" if item.get("confidence") else "-"
        table.add_row(item["id"][:8], item["title"], item["status"], item["priority"], conf)

    console.print(table)


@tasks_app.command("take")
def tasks_take(task_id: str = typer.Argument(help="Work item ID")) -> None:
    """Take a task — assigns you and starts it."""
    data = _post(f"/api/v1/work-items/{task_id}/take")
    console.print(f"[green]Taken:[/green] {data.get('title', task_id)}")


@tasks_app.command("start")
def tasks_start(task_id: str = typer.Argument(help="Work item ID")) -> None:
    """Start a task."""
    data = _post(f"/api/v1/work-items/{task_id}/start")
    console.print(f"[green]Started:[/green] {data.get('title', task_id)}")


@tasks_app.command("complete")
def tasks_complete(task_id: str = typer.Argument(help="Work item ID")) -> None:
    """Complete a task."""
    data = _post(f"/api/v1/work-items/{task_id}/complete")
    console.print(f"[green]Completed:[/green] {data.get('title', task_id)}")


# --- Clusters ---

clusters_app = typer.Typer(help="Manage clusters")
app.add_typer(clusters_app, name="clusters")


@clusters_app.command("list")
def clusters_list() -> None:
    """List registered clusters."""
    data = _get("/api/v1/clusters")
    table = Table(title="Clusters")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Name")
    table.add_column("Endpoint")
    table.add_column("State")

    for c in data["items"]:
        table.add_row(c["id"][:8], c["display_name"], c["api_endpoint"], c["onboarding_state"])

    console.print(table)


# --- Definitions ---

definitions_app = typer.Typer(help="Manage definitions")
app.add_typer(definitions_app, name="definitions")


@definitions_app.command("list")
def definitions_list(kind: str | None = typer.Option(None, help="Filter by kind")) -> None:
    """List definitions."""
    params = {}
    if kind:
        params["kind"] = kind
    data = _get("/api/v1/definitions", params)
    table = Table(title="Definitions")
    table.add_column("Kind")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Enabled")

    for d in data["items"]:
        table.add_row(d["kind"], d["name"], d["version"], str(d["enabled"]))

    console.print(table)


@definitions_app.command("create")
def definitions_create(file: str = typer.Argument(help="Path to definition .md file")) -> None:
    """Create or update a definition from a markdown file."""
    import yaml

    with open(file) as handle:
        content = handle.read()
    if not content.strip().startswith("---"):
        console.print("[red]File must start with YAML frontmatter (---)[/red]")
        raise typer.Exit(1)

    end = content.index("---", 3)
    fm = yaml.safe_load(content[3:end])
    body = content[end + 3:].strip()

    _post("/api/v1/definitions", {
        "kind": fm["kind"],
        "name": fm["name"],
        "version": fm.get("version", "1.0.0"),
        "frontmatter": fm,
        "body": body,
    })
    console.print(f"[green]Created:[/green] {fm['kind']}/{fm['name']}")


# --- Analytics ---

analytics_app = typer.Typer(help="Analytics and ROI")
app.add_typer(analytics_app, name="analytics")


@analytics_app.command("roi")
def analytics_roi(
    since: str = typer.Option("30d", help="Time period"),
    format: str = typer.Option("table", help="Output format"),
) -> None:
    """Show ROI metrics."""
    data = _get("/api/v1/analytics/roi", {"since": since})
    if format == "json":
        console.print_json(json.dumps(data))
    else:
        metrics = data.get("metrics", {})
        table = Table(title=f"ROI Metrics ({data.get('period', since)})")
        table.add_column("Metric")
        table.add_column("Value")
        for k, v in metrics.items():
            table.add_row(k.replace("_", " ").title(), str(v))
        console.print(table)


@analytics_app.command("scanners")
def analytics_scanners(format: str = typer.Option("table", help="Output format")) -> None:
    """Show scanner quality metrics."""
    data = _get("/api/v1/analytics/scanners")
    if format == "json":
        console.print_json(json.dumps(data))
    else:
        table = Table(title="Scanner Quality")
        table.add_column("Scanner")
        table.add_column("Signals")
        for s in data.get("scanners", []):
            table.add_row(s["scanner"], str(s["signal_total"]))
        console.print(table)


if __name__ == "__main__":
    app()
