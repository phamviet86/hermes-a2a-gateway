#!/usr/bin/env python3
"""Validate candidate interpreters before widening release Requires-Python metadata.

Resolve dependencies with their real Python constraints; ignore Requires-Python
only for this project's editable install, with dependency installation disabled.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    dependencies = [*project["dependencies"], *project["optional-dependencies"]["dev"]]
    subprocess.run([sys.executable, "-m", "pip", "install", *dependencies], check=True, cwd=root)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--ignore-requires-python", "-e", ".[dev]"],
        check=True,
        cwd=root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
