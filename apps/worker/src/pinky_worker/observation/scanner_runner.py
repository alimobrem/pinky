"""Scanner runner — legacy module, replaced by generic_scanner.py.

All scanner checks are now defined as structured YAML in scanner definition
frontmatter and executed by the generic scanner executor. This module is
kept for backward compatibility with tests that import from it.
"""

from __future__ import annotations

from pinky_worker.observation.generic_scanner import run_generic_checks

__all__ = ["run_generic_checks"]
