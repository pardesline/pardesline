"""Build ``plugins/pardesline/``: the edition of the Claude Code plugin submitted to the Claude
plugin directory.

The directory accepts from organisations that are not Verified only Markdown, text, JSON, YAML and
images, and no MCP server that runs on the user's machine. The repository's own plugin (root
``.claude-plugin/``) starts the local server and ships the skills' Python reference scripts, so it
is refused there. This edition carries:

- every skill's Markdown (``SKILL.md`` and ``references/*.md``), with a pointer to the scripts in
  the repository instead of the scripts themselves;
- a remote, read-only MCP server: the Hugging Face Space (datasets, algorithms and guides);
- the listing icon.

Run ``python tools/build_directory_plugin.py`` after changing a skill, and commit the result;
``--check`` exits 1 when the folder is out of date (tests/test_directory_plugin.py runs it).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "plugins" / "pardesline"
REMOTE_MCP_URL = "https://jtabet-pardesline.hf.space/gradio_api/mcp/"
REPO = "https://github.com/pardesline/pardesline"


def _version() -> str:
    text = (ROOT / "src" / "pardesline" / "_version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__ = "([^"]+)"', text)
    if not match:
        raise SystemExit("no __version__ in src/pardesline/_version.py")
    return match.group(1)


def _skill_count() -> int:
    return sum(1 for p in (ROOT / "skills").glob("*/SKILL.md") if p.parent.name not in EXCLUDED_SKILLS)


def _plugin_json() -> dict:
    root = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return {
        "name": "pardesline",
        "version": _version(),
        "description": (
            f"3D vision and medical imaging for Claude: {_skill_count()} skills (3D representations, "
            "point-cloud and CT/MR registration, atlas label transfer, PointNet, DINOv3, JEPA, VAE "
            "anomaly detection, Gaussian splatting, medical segmentation models, 3D metrics, datasets "
            "by manifest, the object model, the 73-algorithm catalog) and a read-only MCP server that "
            "browses 43 public datasets with their licences, the algorithms and the guides. Loading "
            "data and running algorithms happen on your machine with the open-source pardesline "
            "package (Apache-2.0)."
        ),
        "author": root["author"],
        "homepage": root["homepage"],
        "repository": root["repository"],
        "license": root["license"],
        "keywords": root["keywords"],
        "mcpServers": {"pardesline": {"type": "http", "url": REMOTE_MCP_URL}},
        "privacyPolicyUrl": f"{REPO}/blob/main/PRIVACY.md",
        "icon": ".claude-plugin/icon.png",
    }


# Left out of the directory edition: the cloud client sends the user's files to the PardesLine
# platform, a service that is not one of the plugin's declared connectors.
EXCLUDED_SKILLS = {"cloud-client"}

# Passages of the other skills that route to the cloud client, removed or reworded in this edition.
# Each must match the source exactly once, so a reworded skill fails the build instead of leaking.
EDITS: dict[str, list[tuple[str, str]]] = {
    "catalog-and-run": [
        (
            " The cloud commands (`login`, `upload`,\n`send`, `inbox`, `ls`, `download`, `share`, `whoami`, "
            "`logout`) are forwarded\nto the cloud client.",
            "",
        ),
    ],
    "using-pardesline": [
        ("),\n  and an optional cloud client. Load this", "). Load this"),
        (
            "scanning-private-folders, medical-volumes, cloud-client, mcp-server,",
            "scanning-private-folders, medical-volumes, mcp-server,",
        ),
        (
            " nothing leaves it. The cloud client is\noptional and separate (`pardesline.cloud`).",
            " nothing leaves it.",
        ),
        (
            "# catalog + object model + cloud client only, no native libs",
            "# catalog + object model only, no native libs",
        ),
        (
            "| share a result, run on the hosted GPU, open a browser viewer | `pl.login()`, `pl.upload`, "
            "`pl.share`, `pardesline.cloud` | cloud-client |\n",
            "",
        ),
        (
            "are the real\nlibraries when installed, the cloud-executed mirrors otherwise.",
            "are the real\nlibraries; install them with the `local` and `medical` extras.",
        ),
    ],
    "contributing-algorithms": [
        ("the 0.1.0 cloud client, verbatim", "the 0.1.0 platform client, verbatim (not in this edition)"),
    ],
}


def _apply_edits(skill: str, text: str) -> str:
    for old, new in EDITS.get(skill, []):
        if text.count(old) != 1:
            raise SystemExit(f"skills/{skill}/SKILL.md: expected one {old[:60]!r}; update EDITS")
        text = text.replace(old, new)
    return text


def _scripts_note(skill: str, scripts: list[str]) -> str:
    names = ", ".join(f"`{s}`" for s in scripts)
    return (
        "\n\n---\n\n"
        "**Reference scripts.** This edition of the skill, from the Claude plugin directory, ships "
        f"text only. The scripts it names ({names}) are in the repository at "
        f"{REPO}/tree/main/skills/{skill}/scripts and inside the `pardesline` Python package, "
        'where the local MCP server returns them with `get_skill(name, file="scripts/...")`.\n'
    )


def _quoted_frontmatter(text: str) -> str:
    """Rewrite the frontmatter's ``key: >-`` folded blocks as one double-quoted line each.

    Same YAML value; the directory's linter asks for text values in double quotes."""
    if not text.startswith("---\n"):
        return text
    end = text.index("\n---\n", 4)
    out: list[str] = []
    key, parts = None, []

    def flush() -> None:
        if key is not None:
            out.append(f"{key}: {json.dumps(' '.join(parts), ensure_ascii=False)}")

    for line in text[4:end].split("\n"):
        if key is not None and line.startswith((" ", "\t")):
            parts.append(line.strip())
            continue
        flush()
        key, parts = None, []
        name, sep, value = line.partition(":")
        if sep and value.strip() in (">-", ">", "|", "|-"):
            if value.strip().startswith("|"):
                raise ValueError(f"literal block for {name!r}: keep frontmatter values folded or plain")
            key = name
        elif sep and value.strip() and not value.strip().startswith('"'):
            out.append(f"{name}: {json.dumps(value.strip(), ensure_ascii=False)}")
        else:
            out.append(line)
    flush()
    return "---\n" + "\n".join(out) + text[end:]


README = """# pardesline: Claude plugin directory edition

Generated by `tools/build_directory_plugin.py` from `skills/` and `.claude-plugin/plugin.json`.
Do not edit by hand: change the skill, run the script, commit both.

This folder is what is submitted to the Claude plugin directory. It holds Markdown, JSON and the
icon only, and declares a remote, read-only MCP server (the Hugging Face Space). The full plugin,
with the local server that loads datasets and runs the algorithms, is the repository root:
`/plugin marketplace add pardesline/pardesline`, then `/plugin install pardesline@pardesline`.
"""


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / ".claude-plugin").mkdir(parents=True)
    (out / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(_plugin_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    shutil.copyfile(ROOT / ".claude-plugin" / "icon.png", out / ".claude-plugin" / "icon.png")
    (out / "README.md").write_text(README, encoding="utf-8", newline="\n")
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        src = skill_md.parent
        if src.name in EXCLUDED_SKILLS:
            continue
        dst = out / "skills" / src.name
        scripts = sorted(p.name for p in (src / "scripts").glob("*.py")) if (src / "scripts").is_dir() else []
        for md in sorted(src.rglob("*.md")):
            rel = md.relative_to(src)
            if rel.parts[0] == "scripts":
                continue
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            text = md.read_text(encoding="utf-8").replace("\r\n", "\n")
            if rel == Path("SKILL.md"):
                text = _quoted_frontmatter(_apply_edits(src.name, text))
                if scripts:
                    text = text.rstrip("\n") + _scripts_note(src.name, scripts)
            target.write_text(text, encoding="utf-8", newline="\n")


def _snapshot(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if plugins/pardesline is out of date")
    args = parser.parse_args(argv)
    if not args.check:
        build(OUT)
        print(f"wrote {OUT.relative_to(ROOT)} ({len(_snapshot(OUT))} files)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "pardesline"
        build(fresh)
        want, have = _snapshot(fresh), _snapshot(OUT) if OUT.is_dir() else {}
    stale = sorted(k for k in want.keys() | have.keys() if want.get(k) != have.get(k))
    if stale:
        print(
            "plugins/pardesline is out of date; run python tools/build_directory_plugin.py:",
            *stale,
            sep="\n  ",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
