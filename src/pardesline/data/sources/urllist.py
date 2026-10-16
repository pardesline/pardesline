"""A dataset published as a plain text index: one download URL per line.

MedShapeNet ships its 106 101 shapes this way (``MedShapeNetDataset.txt``,
one STL per URL). The index is fetched once and cached; the relative path of
an entry is the URL's path after ``strip_prefix`` (default: its file name).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from loguru import logger

from ...errors import FetchError
from ..cache import cache_dir, dataset_cache_dir

__all__ = ["UrlListSource"]


class UrlListSource:
    """One file per line of a remote text index (MedShapeNet), fetched by URL with Range support."""

    def __init__(
        self,
        name: str,
        index_url: str,
        *,
        strip_prefix: str | None = None,
        max_files: int = 200000,
        cache: Path | None = None,
    ):
        self.name = name
        self.index_url = index_url
        self.strip_prefix = strip_prefix
        self.max_files = max_files
        self.cache = cache if cache is not None else dataset_cache_dir(name)
        self._urls: dict[str, str] | None = None

    def _relpath(self, url: str) -> str:
        path = unquote(urlparse(url).path)
        if self.strip_prefix and self.strip_prefix in path:
            return path.split(self.strip_prefix, 1)[1].lstrip("/")
        return path.rsplit("/", 1)[-1]

    def _index(self) -> dict[str, str]:
        if self._urls is not None:
            return self._urls
        key = hashlib.sha1(self.index_url.encode()).hexdigest()[:16]
        folder = cache_dir() / "url-indexes"
        folder.mkdir(parents=True, exist_ok=True)
        cached = folder / f"{key}.json"
        if cached.is_file():
            try:
                self._urls = json.loads(cached.read_text(encoding="utf-8"))["urls"]
                return self._urls
            except (OSError, ValueError, KeyError):
                pass
        try:
            r = httpx.get(self.index_url, follow_redirects=True, timeout=300)
        except httpx.HTTPError as exc:
            raise FetchError(f"cannot fetch the index {self.index_url}: {exc}") from None
        if r.status_code != 200:
            raise FetchError(f"cannot fetch the index {self.index_url}: HTTP {r.status_code}")
        urls: dict[str, str] = {}
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or not line.startswith(("http://", "https://")):
                continue
            rel = self._relpath(line)
            if rel in urls:
                rel = rel  # duplicates keep the first url; the manifest's pattern decides
                continue
            urls[rel] = line
            if len(urls) > self.max_files:
                raise FetchError(
                    f"{self.index_url}: more than {self.max_files} entries; raise source.max_files."
                )
        if not urls:
            raise FetchError(f"{self.index_url}: no URL found in the index")
        self._urls = urls
        try:
            cached.write_text(json.dumps({"index_url": self.index_url, "urls": urls}), encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            logger.debug("url index not cached: {}", exc)
        return urls

    def list(self) -> list[str]:
        return sorted(self._index())

    def fetch(self, relpath: str) -> Path:
        urls = self._index()
        if relpath not in urls:
            raise FetchError(f"{relpath!r} is not in the index {self.index_url}")
        target = self.cache / relpath
        if target.is_file() and target.stat().st_size > 0:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        url = urls[relpath]
        fd, tmp_name = tempfile.mkstemp(prefix="pardesline-", dir=target.parent)
        tmp = Path(tmp_name)
        logger.info("{}: fetching {}", self.name, url)
        try:
            with open(fd, "wb") as out, httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
                if r.status_code != 200:
                    raise FetchError(f"HTTP {r.status_code} for {url}")
                for chunk in r.iter_bytes(1 << 20):
                    out.write(chunk)
        except (httpx.HTTPError, OSError) as exc:
            tmp.unlink(missing_ok=True)
            raise FetchError(f"cannot fetch {url}: {exc}") from None
        except FetchError:
            tmp.unlink(missing_ok=True)
            raise
        shutil.move(str(tmp), target)
        return target

    def describe(self) -> str:
        return f"url index {self.index_url}, files cached in {self.cache}"
