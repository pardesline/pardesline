"""Sources: where a manifest's files come from and how one is fetched.

Every source answers two questions: ``fetch(relpath) -> local Path`` (download,
verify, cache) and ``list() -> relpaths or None`` when listing is possible.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..manifest import Manifest, SourceSpec

__all__ = ["Source", "open_source"]


class Source(Protocol):
    def fetch(self, relpath: str) -> Path: ...

    def list(self) -> list[str] | None: ...

    def describe(self) -> str: ...


def open_source(spec: SourceSpec, manifest: Manifest, *, manifest_dir: Path | None = None) -> Source:
    if spec.scheme == "local":
        from .local import LocalSource

        root = Path(spec.root or ".")
        if not root.is_absolute() and manifest_dir is not None:
            root = manifest_dir / root
        return LocalSource(root)
    if spec.scheme == "https":
        from .https import HttpsSource

        return HttpsSource(manifest.name, spec.files or {}, spec.mirrors)
    if spec.scheme == "hf":
        from .hf import HfSource

        return HfSource(spec.repo_id or "", revision=spec.revision, repo_type=spec.repo_type)
    if spec.scheme == "open3d":
        from .open3d import Open3DSource

        return Open3DSource(spec.dataset or "")
    raise ValueError(f"unknown source scheme {spec.scheme!r}")
