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


def test_directory_edition_does_not_route_to_the_cloud_client():
    """The edition sends nothing to a service other than its declared, read-only connector."""
    cloud = re.compile(
        r"cloud-client|pardesline\.cloud|appbeta|pl\.(login|upload|send|share|inbox)\b|cloud client"
    )
    for md in PLUGIN.rglob("*.md"):
        for line in md.read_text(encoding="utf-8").splitlines():
            assert not cloud.search(line), f"{md.relative_to(PLUGIN)}: {line[:80]}"
    assert (
        str(len(list((PLUGIN / "skills").glob("*/SKILL.md"))))
        in json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["description"]
    )


def test_directory_skill_frontmatter_values_are_double_quoted():
    """The directory's YAML lint asks for text values in double quotes (no folded blocks)."""
    for skill_md in (PLUGIN / "skills").glob("*/SKILL.md"):
        frontmatter = skill_md.read_text(encoding="utf-8").split("---\n")[1]
        for line in frontmatter.strip().splitlines():
            key, _, value = line.partition(": ")
            assert key in {"name", "description"}, f"{skill_md}: {line[:60]}"
            assert value.startswith('"') and value.endswith('"'), f"{skill_md}: {line[:60]}"
            assert json.loads(value), f"{skill_md}: {key}"
