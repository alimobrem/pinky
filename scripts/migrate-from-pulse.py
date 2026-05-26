#!/usr/bin/env python3
"""Translate Pulse scanner configs to Pinky scanner markdown definitions.

Usage:
    python scripts/migrate-from-pulse.py --input-dir /path/to/pulse/configs --dry-run
    python scripts/migrate-from-pulse.py --input-dir /path/to/pulse/configs --output-dir definitions/scanners/ --write
"""
import argparse
import sys
from pathlib import Path

import yaml


def translate_scanner(config: dict, source_file: str) -> str:
    """Translate a Pulse scanner config to Pinky markdown format.

    Args:
        config: Parsed YAML config from Pulse
        source_file: Source filename for reference

    Returns:
        Markdown content with YAML frontmatter
    """
    name = config.get("name", Path(source_file).stem)
    description = config.get("description", f"Migrated from Pulse: {source_file}")
    resource_kinds = config.get("resource_kinds", ["Pod"])
    interval = config.get("interval", "5m")

    frontmatter = {
        "name": name,
        "type": "scanner",
        "resource_kinds": resource_kinds,
        "interval": interval,
        "origin": "pulse",
    }

    yaml_fm = yaml.dump(frontmatter, default_flow_style=False).strip()
    body = config.get("description", f"Scanner migrated from Pulse config: {source_file}")

    return f"---\n{yaml_fm}\n---\n\n{body}\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate Pulse configs to Pinky scanner definitions"
    )
    parser.add_argument("--input-dir", required=True, help="Directory containing Pulse YAML configs")
    parser.add_argument("--output-dir", default="definitions/scanners/", help="Output directory for scanner definitions")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview without writing (default)")
    parser.add_argument("--write", action="store_true", help="Write scanner definitions to disk")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: {input_dir} does not exist")
        sys.exit(1)

    configs = list(input_dir.glob("*.yaml")) + list(input_dir.glob("*.yml"))
    if not configs:
        print(f"No YAML files found in {input_dir}")
        sys.exit(0)

    for config_file in configs:
        with open(config_file) as f:
            config = yaml.safe_load(f)

        if not config:
            continue

        md_content = translate_scanner(config, str(config_file))
        output_file = output_dir / f"{config_file.stem}.md"

        if args.write:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(md_content)
            print(f"Created: {output_file}")
        else:
            print(f"\n--- Would create: {output_file} ---")
            print(md_content)

    action = "Wrote" if args.write else "Would write"
    print(f"\n{action} {len(configs)} scanner definitions")


if __name__ == "__main__":
    main()
