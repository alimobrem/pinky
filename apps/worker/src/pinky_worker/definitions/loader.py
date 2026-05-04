"""Definition loader — parses MD files with YAML frontmatter.

Loads from filesystem (definitions/ directory) as defaults.
DB definitions (via API) take precedence over filesystem for same (kind, name).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Definition:
    kind: str
    name: str
    version: str
    frontmatter: dict
    body: str
    source: str  # "filesystem" | "database"
    enabled: bool = True

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.name)


KIND_DIRS = {
    "scanner": "scanners",
    "tool": "tools",
    "skill": "skills",
    "pipeline": "pipelines",
    "policy": "policies",
    "redaction-rule": "redaction-rules",
    "approval-policy": "approval-policies",
}


def parse_md_definition(content: str, source: str = "filesystem") -> Definition:
    content = content.strip()
    if not content.startswith("---"):
        raise ValueError("Definition must start with YAML frontmatter (---)")

    end = content.index("---", 3)
    frontmatter_raw = content[3:end].strip()
    body = content[end + 3:].strip()

    fm = yaml.safe_load(frontmatter_raw)
    if not isinstance(fm, dict):
        raise ValueError("Frontmatter must be a YAML mapping")

    kind = fm.get("kind", "")
    name = fm.get("name", "")
    version = fm.get("version", "1.0.0")

    if not kind or not name:
        raise ValueError(f"Frontmatter must include 'kind' and 'name', got kind={kind!r} name={name!r}")

    return Definition(
        kind=kind,
        name=name,
        version=str(version),
        frontmatter=fm,
        body=body,
        source=source,
        enabled=fm.get("enabled", True),
    )


def load_from_directory(definitions_dir: str | Path) -> list[Definition]:
    definitions_dir = Path(definitions_dir)
    results: list[Definition] = []

    for kind, dirname in KIND_DIRS.items():
        kind_dir = definitions_dir / dirname
        if not kind_dir.is_dir():
            continue

        for md_file in sorted(kind_dir.glob("*.md")):
            content = md_file.read_text()
            try:
                defn = parse_md_definition(content, source="filesystem")
                if defn.kind != kind:
                    raise ValueError(f"File in {dirname}/ declares kind={defn.kind!r}, expected {kind!r}")
                results.append(defn)
            except Exception as e:
                raise ValueError(f"Failed to parse {md_file}: {e}") from e

    return results


class DefinitionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], Definition] = {}

    def load_filesystem(self, definitions_dir: str | Path) -> int:
        defs = load_from_directory(definitions_dir)
        for d in defs:
            self._definitions[d.key] = d
        return len(defs)

    def load_database_overrides(self, db_definitions: list[Definition]) -> int:
        count = 0
        for d in db_definitions:
            self._definitions[d.key] = d
            count += 1
        return count

    def get(self, kind: str, name: str) -> Definition | None:
        return self._definitions.get((kind, name))

    def list_by_kind(self, kind: str) -> list[Definition]:
        return [d for d in self._definitions.values() if d.kind == kind and d.enabled]

    def all(self) -> list[Definition]:
        return list(self._definitions.values())

    @property
    def count(self) -> int:
        return len(self._definitions)
