# Pinky CLI

Command-line interface for Pinky, wrapping the REST API with a human-friendly terminal experience.

## Installation

```bash
cd apps/cli
pip install -e .
```

## Configuration

```bash
export PINKY_API_URL=http://localhost:8000   # API server URL (default)
```

> **Note:** Token-based authentication (`PINKY_API_TOKEN`) is not yet implemented. The CLI currently makes unauthenticated requests to the API.

## Commands

```
pinky tasks list              List work items (filterable by status, priority, cluster)
pinky tasks take <id>         Take ownership of a task
pinky tasks start <id>        Transition task to in_progress
pinky tasks complete <id>     Mark task as done

pinky clusters list           List registered clusters with binding status

pinky definitions list        List all definitions (scanners, tools, skills, policies)
pinky definitions create <f>  Create/update a definition from a markdown file

pinky analytics roi           Show ROI metrics (time saved, issues resolved)
pinky analytics scanners      Show scanner detection statistics
```

## Testing

```bash
cd apps/cli
.venv/bin/pytest tests/ -v   # 18 tests
```
