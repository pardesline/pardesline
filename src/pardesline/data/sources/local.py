from __future__ import annotations

from pathlib import Path

from ...object import SIDECAR_SUFFIX

__all__ = ["LocalSource"]

_SKIP_DIRS = {".git", "__pycache__", ".pardesline", "node_modules"}


class LocalSource:
    """Files already on disk under ``root``."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"dataset folder not found: {self.root}")

    def fetch(self, relpath: str) -> Path:
        p = self.root / relpath
        if not p.exists():
            raise FileNotFoundError(f"{relpath!r} is not under {self.root}")
        return p

    def list(self) -> list[str]:
        out: list[str] = []
        for p in sorted(self.root.rglob("*")):
            if any(
                part.startswith(".") or part in _SKIP_DIRS for part in p.relative_to(self.root).parts[:-1]
            ):
                continue
            if p.is_file() and not p.name.startswith(".") and not p.name.endswith(SIDECAR_SUFFIX):
                out.append(p.relative_to(self.root).as_posix())
        return out

    def describe(self) -> str:
        return f"local folder {self.root}"
