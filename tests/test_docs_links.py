"""Current docs resolve; immutable pre-v0.12 link defects cannot silently expand."""

import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LEGACY_BROKEN = {
    ("docs/reports/testing-report-v0.9.0.md", "upgrade-v0.9.md"),
    ("docs/reports/testing-report-v0.10.0.md", "client-antigravity.vi.md"),
    ("docs/reports/testing-report-v0.10.0.md", "antigravity.md"),
    ("docs/reports/testing-report-v0.8.0.md", "deployment.md#upgrade-and-rollback"),
    ("docs/history/durable-jobs.md", "client-server-deployment.md"),
    ("docs/history/setup-codex-hermes.vi.md", "server-hermes.vi.md"),
    ("docs/history/setup-codex-hermes.vi.md", "client-codex.vi.md"),
    ("docs/history/deployment.md", "client-server-deployment.md"),
    ("docs/history/agent-setup.md", "server-hermes.vi.md"),
    ("docs/history/agent-setup.md", "client-codex.vi.md"),
}


def local_links(file):
    text = re.sub(r"^\s*(```|~~~).*?^\s*\1\s*$", "", file.read_text(), flags=re.M | re.S)
    targets = re.findall(r"\]\(([^)\n]+)\)", text)
    targets += re.findall(r"^\s*\[[^\]]+\]:\s*(\S+)", text, flags=re.M)
    for target in targets:
        target = target.strip()
        target = target[1 : target.index(">")] if target.startswith("<") else target.split()[0]
        value = urlsplit(target)
        if value.scheme or value.netloc or not value.path:
            continue
        yield target, (file.parent / unquote(value.path)).resolve()


def test_documentation_relative_paths_have_no_new_failures():
    broken = set()
    for file in (ROOT / "docs").rglob("*.md"):
        for target, path in local_links(file):
            if not path.exists():
                broken.add((file.relative_to(ROOT).as_posix(), target))
    assert broken == LEGACY_BROKEN, f"New/missing legacy defects: {broken ^ LEGACY_BROKEN}"


def test_task_index_lists_each_current_guide_and_contract_exactly_once():
    files = {*(ROOT / "docs/guides").glob("*.md"), *(ROOT / "docs/reference").glob("*.md")}
    counts = Counter(path for _, path in local_links(ROOT / "docs/README.md"))
    assert {path.name: counts[path] for path in files if counts[path] != 1} == {}
