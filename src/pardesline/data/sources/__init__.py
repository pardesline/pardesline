"""Sources: where a manifest's files come from and how one is fetched.

Every source answers two questions: ``fetch(relpath) -> local Path`` (download,
verify, cache) and ``list() -> relpaths or None`` when listing is possible.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..manifest import Manifest, SourceSpec

__all__ = ["Source", "fetch_folder", "open_source"]


class Source(Protocol):
    def fetch(self, relpath: str) -> Path: ...

    def list(self) -> list[str] | None: ...

    def describe(self) -> str: ...


def fetch_folder(source: Source, prefix: str) -> Path:
    """Every file under ``prefix`` (a DICOM series): the source's own
    ``fetch_folder`` when it has one, else file by file from the listing."""
    impl = getattr(source, "fetch_folder", None)
    if impl is not None:
        return impl(prefix)
    prefix = prefix.rstrip("/") + "/"
    listing = source.list() or []
    members = [rel for rel in listing if rel.startswith(prefix)]
    if not members:
        raise FileNotFoundError(f"no file under {prefix!r} in {source.describe()}")
    paths = [source.fetch(rel) for rel in members]
    folder = paths[0].parent
    return folder


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

        return HfSource(
            spec.repo_id or "",
            revision=spec.revision,
            repo_type=spec.repo_type,
            paths=spec.paths,
            max_files=spec.max_files,
        )
    if spec.scheme == "open3d":
        from .open3d import Open3DSource

        return Open3DSource(spec.dataset or "")
    if spec.scheme == "archive":
        from .archive import RemoteArchiveSource

        return RemoteArchiveSource(
            manifest.name,
            spec.archive_urls,
            format=spec.archive_format,
            prefix=spec.prefix,
            sha512=spec.sha512,
            md5=spec.md5,
        )
    if spec.scheme == "s3":
        from .s3 import S3Source

        return S3Source(
            manifest.name,
            spec.bucket or "",
            endpoint=spec.endpoint,
            prefix=spec.prefix,
            max_files=spec.max_files,
        )
    if spec.scheme == "tcia":
        from .tcia import TciaSource

        return TciaSource(manifest.name, spec.collection or "", modalities=spec.modalities, api=spec.api)
    if spec.scheme == "urllist":
        from .urllist import UrlListSource

        return UrlListSource(
            manifest.name, spec.index_url or "", strip_prefix=spec.strip_prefix, max_files=spec.max_files
        )
    raise ValueError(f"unknown source scheme {spec.scheme!r}")
