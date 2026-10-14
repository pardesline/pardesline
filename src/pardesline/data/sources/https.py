"""Download-on-demand source with SHA-512 verification and a local cache.

A file entry carries its hash and optionally an explicit URL and an
``archive`` flag (the download is a tar/zip whose content lands in the
file's folder — e.g. a MetaImage header + its .raw). Without a URL the
hash-addressed mirrors are tried in order.
"""

from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

import httpx
from loguru import logger

from ...errors import FetchError
from ..cache import dataset_cache_dir
from ..manifest import DEFAULT_MIRRORS, FileSpec

__all__ = ["HttpsSource", "sha512_of"]

_CHUNK = 1 << 20


def sha512_of(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _matches(path: Path, spec: FileSpec) -> bool:
    if spec.sha512:
        return sha512_of(path) == spec.sha512
    h = hashlib.md5()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest() == spec.md5


def _safe_extract(archive: Path, into: Path) -> None:
    """Extract without letting a member escape ``into``."""
    into = into.resolve()

    def ok(name: str) -> bool:
        target = (into / name).resolve()
        return target == into or into in target.parents

    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            members = [m for m in tf.getmembers() if ok(m.name) and not m.issym() and not m.islnk()]
            tf.extractall(into, members=members)
        return
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if ok(info.filename):
                    zf.extract(info, into)
        return
    raise FetchError(f"{archive.name} is neither a tar nor a zip archive.")


class HttpsSource:
    def __init__(
        self,
        name: str,
        files: dict[str, FileSpec],
        mirrors: list[str] | None = None,
        *,
        cache: Path | None = None,
    ):
        self.name = name
        self.files = files
        self.mirrors = list(mirrors) if mirrors else list(DEFAULT_MIRRORS)
        self.cache = cache if cache is not None else dataset_cache_dir(name)

    def list(self) -> list[str]:
        return list(self.files)

    def describe(self) -> str:
        return f"{len(self.files)} file(s) over https, cached in {self.cache}"

    def _urls(self, spec: FileSpec) -> list[str]:
        urls = [spec.url] if spec.url else []
        urls += [m.format(sha512=spec.sha512) for m in self.mirrors]
        return urls

    def fetch(self, relpath: str) -> Path:
        if relpath not in self.files:
            raise FetchError(f"{relpath!r} is not declared in the manifest of {self.name!r}.")
        spec = self.files[relpath]
        target = self.cache / relpath
        if target.exists():
            # Archive members are verified at download time only (the hash is the archive's).
            if spec.archive or _matches(target, spec):
                return target
            logger.warning("cached {} has a different hash; downloading again", relpath)
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        errors = []
        for url in self._urls(spec):
            try:
                tmp = self._download(url, spec)
            except FetchError as exc:
                errors.append(f"{url}: {exc}")
                continue
            if spec.archive:
                into = target.parent if spec.archive_root is None else (self.cache / spec.archive_root)
                _safe_extract(tmp, into)
                tmp.unlink(missing_ok=True)
                if not target.exists():
                    raise FetchError(
                        f"archive from {url} did not contain {relpath!r}. "
                        "Members land next to the declared path."
                    )
            else:
                shutil.move(str(tmp), target)
            return target
        raise FetchError(f"could not fetch {relpath!r}:\n  " + "\n  ".join(errors))

    def _download(self, url: str, spec: FileSpec) -> Path:
        h = hashlib.sha512() if spec.sha512 else hashlib.md5()
        fd, tmp_name = tempfile.mkstemp(prefix="pardesline-", dir=self.cache)
        tmp = Path(tmp_name)
        logger.info("downloading {}", url)
        try:
            with open(fd, "wb") as out, httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                if r.status_code != 200:
                    raise FetchError(f"HTTP {r.status_code}")
                total = int(r.headers.get("content-length") or 0)
                done = 0
                next_report = 0.1
                for chunk in r.iter_bytes(_CHUNK):
                    out.write(chunk)
                    h.update(chunk)
                    done += len(chunk)
                    if total and done / total >= next_report:
                        logger.debug("  {:.0f}% of {:.1f} MB", 100 * done / total, total / 1e6)
                        next_report += 0.1
        except (httpx.HTTPError, OSError) as exc:
            tmp.unlink(missing_ok=True)
            raise FetchError(str(exc)) from None
        except FetchError:
            tmp.unlink(missing_ok=True)
            raise
        if h.hexdigest() != (spec.sha512 or spec.md5):
            tmp.unlink(missing_ok=True)
            raise FetchError(
                f"{'SHA-512' if spec.sha512 else 'MD5'} mismatch - "
                "the file is not the one the manifest describes"
            )
        return tmp
