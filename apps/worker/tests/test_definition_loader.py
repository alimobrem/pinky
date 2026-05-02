from pathlib import Path

import pytest

from pinky_worker.definitions.loader import DefinitionRegistry, load_from_directory, parse_md_definition

DEFINITIONS_DIR = Path(__file__).parent.parent.parent.parent / "definitions"


def test_parse_scanner_definition() -> None:
    content = """---
name: test-scanner
kind: scanner
version: 1.0.0
resource_kinds: [Pod]
---
# Test Scanner
Checks pods.
"""
    d = parse_md_definition(content)
    assert d.kind == "scanner"
    assert d.name == "test-scanner"
    assert d.version == "1.0.0"
    assert d.frontmatter["resource_kinds"] == ["Pod"]
    assert "Checks pods" in d.body


def test_parse_rejects_missing_frontmatter() -> None:
    with pytest.raises(ValueError, match="must start with YAML frontmatter"):
        parse_md_definition("# No frontmatter")


def test_parse_rejects_missing_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        parse_md_definition("---\nname: foo\n---\nbody")


def test_parse_rejects_missing_name() -> None:
    with pytest.raises(ValueError, match="name"):
        parse_md_definition("---\nkind: scanner\n---\nbody")


def test_load_from_definitions_directory() -> None:
    if not DEFINITIONS_DIR.exists():
        pytest.skip("definitions/ directory not found")
    defs = load_from_directory(DEFINITIONS_DIR)
    assert len(defs) >= 8  # 2 scanners + 2 tools + 1 skill + 1 pipeline + 2 policies + 1 redaction
    kinds = {d.kind for d in defs}
    assert "scanner" in kinds
    assert "tool" in kinds
    assert "skill" in kinds
    assert "pipeline" in kinds
    assert "policy" in kinds
    assert "redaction-rule" in kinds


def test_registry_filesystem_and_db_override() -> None:
    registry = DefinitionRegistry()
    registry.load_filesystem(DEFINITIONS_DIR)
    assert registry.count >= 8

    scanners = registry.list_by_kind("scanner")
    assert len(scanners) >= 2

    pod_health = registry.get("scanner", "pod-health")
    assert pod_health is not None
    assert pod_health.source == "filesystem"

    # DB override takes precedence
    db_override = parse_md_definition("""---
name: pod-health
kind: scanner
version: 2.0.0
---
# Overridden pod health scanner
""", source="database")
    registry.load_database_overrides([db_override])

    pod_health_v2 = registry.get("scanner", "pod-health")
    assert pod_health_v2 is not None
    assert pod_health_v2.version == "2.0.0"
    assert pod_health_v2.source == "database"
