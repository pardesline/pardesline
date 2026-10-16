"""Locate and run the reference scripts shipped with the expert skills (inside the wheel or the repo)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pardesline.mcp_server import skills_dir


def script(skill: str, name: str) -> Path:
    path = skills_dir() / skill / "scripts" / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def run(skill: str, name: str, *args: str) -> None:
    cmd = [sys.executable, str(script(skill, name)), *args]
    print("$", " ".join(cmd[1:]), flush=True)
    subprocess.run(cmd, check=True)
