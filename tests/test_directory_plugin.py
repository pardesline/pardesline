"""plugins/pardesline, the Claude plugin directory edition, stays in sync with skills/ and holds only
what the directory accepts from an organisation that is not Verified: Markdown, JSON and images,
nothing starting with #!, no line that changes where a package manager gets packages, and no MCP
server started on the user's machine."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pardesline as pl

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "pardesline"
ALLOWED = {".md", ".json", ".png"}
PACKAGE_SOURCE = re.compile(r"git\+|--(extra-)?index-url|--find-links|\bregistry\s*=|\s-i\s+https?://")


def test_directory_plugin_is_up_to_date():
    run = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_directory_plugin.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr


def test_directory_plugin_holds_only_accepted_files():
    files = [p for p in PLUGIN.rglob("*") if p.is_file()]
    assert files
    for path in files:
        rel = path.relative_to(PLUGIN).as_posix()
        assert path.suffix in ALLOWED, rel
        data = path.read_bytes()
        assert not data.startswith(b"#!"), rel
        if path.suffix != ".png":
            text = data.decode("utf-8")  # UTF-8, no NUL
            assert "\x00" not in text, rel
            for line in text.splitlines():
                assert not PACKAGE_SOURCE.search(line), f"{rel}: {line}"


def test_directory_plugin_declares_only_a_remote_server():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["version"] == pl.__version__
    for name, server in manifest["mcpServers"].items():
        assert "command" not in server, name
        assert server["type"] == "http" and server["url"].startswith("https://"), name
    skills = {p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md")}
    assert skills == {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
