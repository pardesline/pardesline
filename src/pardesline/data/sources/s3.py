"""A public S3 bucket (or S3-compatible store) listed with ListObjectsV2 and
read over plain HTTPS. No credentials, no SDK.

OpenNeuro publishes every dataset this way (``s3://openneuro.org/ds000228/``,
CC0), so do several challenge hosts. Keys are listed under the manifest's
``prefix`` (paginated, capped, cached on disk) and each object is fetched on
demand into the dataset cache.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

import httpx
from loguru import logger

from ...errors import FetchError
from ..cache import cache_dir, dataset_cache_dir

__all__ = ["S3Source"]

_KEY = re.compile(r"<Key>([^<]+)</Key>")
_TRUNCATED = re.compile(r"<IsTruncated>([^<]+)</IsTruncated>")
_TOKEN = re.compile(r"<NextContinuationToken>([^<]+)</NextContinuationToken>")
_ETAG = re.compile(r"<ETag>&quot;([^&]+)&quot;</ETag>|<ETag>\"([^\"]+)\"</ETag>")


def _unescape(s: str) -> str:
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


class S3Source:
    """Objects of a public S3 bucket listed with ``ListObjectsV2`` (anonymous) and fetched by key.

    Used for OpenNeuro (``s3://openneuro.org/dsXXXXXX``); no credentials, no SDK.
    """

    def __init__(
        self,
        name: str,
        bucket: str,
        *,
        endpoint: str = "https://s3.amazonaws.com",
        prefix: str | None = None,
        max_files: int = 20000,
        cache: Path | None = None,
    ):
        self.name = name
        self.bucket = bucket
        self.endpoint = endpoint.rstrip("/")
        self.prefix = (prefix or "").strip("/")
        self.prefix_slash = self.prefix + "/" if self.prefix else ""
        self.max_files = max_files
        self.cache = cache if cache is not None else dataset_cache_dir(name)
        self._listing: list[str] | None = None

    # ---- URLs ---------------------------------------------------------------
    @property
    def bucket_url(self) -> str:
        if self.endpoint == "https://s3.amazonaws.com":
            return f"https://s3.amazonaws.com/{self.bucket}"
        return f"{self.endpoint}/{self.bucket}"

    def object_url(self, relpath: str) -> str:
        return f"{self.bucket_url}/{self.prefix_slash}{relpath}"

    def _listing_cache(self) -> Path:
        key = hashlib.sha1(f"{self.bucket_url}/{self.prefix}".encode()).hexdigest()[:16]
        folder = cache_dir() / "s3-listings"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{self.bucket.replace('/', '_')}_{key}.json"

    # ---- Source protocol ----------------------------------------------------
    def list(self) -> list[str]:
        if self._listing is not None:
            return self._listing
        cached = self._listing_cache()
        if cached.is_file():
            try:
                self._listing = json.loads(cached.read_text(encoding="utf-8"))["keys"]
                return self._listing
            except (OSError, ValueError, KeyError):
                pass
        keys: list[str] = []
        token: str | None = None
        with httpx.Client(follow_redirects=True, timeout=60) as c:
            while True:
                params = {"list-type": "2", "max-keys": "1000"}
                if self.prefix_slash:
                    params["prefix"] = self.prefix_slash
                if token:
                    params["continuation-token"] = token
                try:
                    r = c.get(self.bucket_url + "/", params=params)
                except httpx.HTTPError as exc:
                    raise FetchError(f"cannot list {self.bucket_url}: {exc}") from None
                if r.status_code == 403:
                    raise FetchError(
                        f"{self.bucket_url}: the bucket does not allow anonymous listing. Give the files "
                        "explicitly (manifest samples) or use an https source."
                    )
                if r.status_code != 200:
                    raise FetchError(f"cannot list {self.bucket_url}: HTTP {r.status_code}")
                text = r.text
                for k in _KEY.findall(text):
                    k = _unescape(k)
                    if k.endswith("/"):
                        continue
                    keys.append(k[len(self.prefix_slash) :] if self.prefix_slash else k)
                    if len(keys) > self.max_files:
                        raise FetchError(
                            f"s3://{self.bucket}/{self.prefix}: more than {self.max_files} objects. "
                            "Narrow the prefix (pl.load('s3://bucket/deeper/prefix')) "
                            "or raise source.max_files."
                        )
                truncated = _TRUNCATED.search(text)
                m = _TOKEN.search(text)
                if truncated and truncated.group(1) == "true" and m:
                    token = _unescape(m.group(1))
                    continue
                break
        keys.sort()
        self._listing = keys
        try:
            cached.write_text(
                json.dumps({"bucket": self.bucket_url, "prefix": self.prefix, "keys": keys}), encoding="utf-8"
            )
        except OSError as exc:  # pragma: no cover
            logger.debug("s3 listing not cached: {}", exc)
        return keys

    def fetch(self, relpath: str) -> Path:
        target = self.cache / relpath
        if target.is_file() and target.stat().st_size > 0:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        url = self.object_url(relpath)
        fd, tmp_name = tempfile.mkstemp(prefix="pardesline-", dir=target.parent)
        tmp = Path(tmp_name)
        logger.info("{}: fetching {}", self.name, url)
        try:
            with open(fd, "wb") as out, httpx.stream("GET", url, follow_redirects=True, timeout=300) as r:
                if r.status_code == 404:
                    raise FetchError(f"{relpath!r} is not in s3://{self.bucket}/{self.prefix}")
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

    def fetch_folder(self, prefix: str) -> Path:
        """Every object under ``prefix`` (a DICOM series stored as files)."""
        prefix = prefix.rstrip("/") + "/"
        members = [k for k in self.list() if k.startswith(prefix)]
        if not members:
            raise FetchError(f"no object under {prefix!r} in s3://{self.bucket}/{self.prefix}")
        for k in members:
            self.fetch(k)
        return self.cache / prefix.rstrip("/")

    def describe(self) -> str:
        return f"s3://{self.bucket}/{self.prefix} ({self.endpoint}), cached in {self.cache}"
