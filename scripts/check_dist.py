#!/usr/bin/env python3
"""Fail if built distributions contain local/runtime artifacts."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.specifiers import SpecifierSet

FORBIDDEN_NAMES = {
    ".coverage",
    ".ds_store",
    ".env",
}
FORBIDDEN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {
    ".bak",
    ".db",
    ".log",
    ".pem",
    ".pyc",
    ".sqlite",
    ".sqlite3",
}


def members(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return archive.getnames()
    raise ValueError(f"unsupported distribution: {path}")


def unsafe(name: str) -> bool:
    parts = {part.lower() for part in Path(name).parts}
    leaf = Path(name).name.lower()
    return bool(
        parts & FORBIDDEN_PARTS
        or leaf in FORBIDDEN_NAMES
        or Path(leaf).suffix in FORBIDDEN_SUFFIXES
        or leaf.startswith("worker-context-")
    )


def metadata_versions(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            data = archive.read(next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA")))
    else:
        with tarfile.open(path, "r:gz") as archive:
            member = next(
                item for item in archive.getmembers() if item.name.count("/") == 1 and item.name.endswith("/PKG-INFO")
            )
            file = archive.extractfile(member)
            assert file is not None
            data = file.read()
    metadata = BytesParser().parsebytes(data)
    spec = SpecifierSet(metadata["Requires-Python"])
    versions = [value for value in ("3.11", "3.12", "3.13") if spec.contains(value)]
    classifiers = {
        value.removeprefix("Programming Language :: Python :: ")
        for value in metadata.get_all("Classifier", [])
        if value.startswith("Programming Language :: Python :: 3.")
    }
    if classifiers != set(versions) or not versions or spec.contains("3.10") or spec.contains("3.14"):
        raise ValueError("Python classifiers and supported interpreter bounds disagree")
    return versions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    distributions = sorted([*args.directory.glob("*.whl"), *args.directory.glob("*.tar.gz")])
    if not distributions:
        parser.error("no wheel or sdist found")
    violations = [(path.name, name) for path in distributions for name in members(path) if unsafe(name)]
    if violations:
        for distribution, name in violations:
            print(f"forbidden distribution member: {distribution}: {name}")
        return 1
    for path in distributions:
        names = members(path)
        required = ("__init__.py", "cli.py", "broker.py", "client.py", "client_mcp.py", "ssh_tunnel.py")
        for module in required:
            if not any(name.endswith("hermes_a2a_gateway/" + module) for name in names):
                print(f"missing runtime module: {path.name}: {module}")
                return 1
        forbidden = {"codex_a2a_gateway", "hermes_plugin", "skills"}
        if any(set(Path(name).parts) & forbidden for name in names):
            print(f"removed legacy package/assets remain: {path.name}")
            return 1
        versions = metadata_versions(path)
        print(f"checked {path.name}: {len(members(path))} members; advertised Python: {', '.join(versions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
