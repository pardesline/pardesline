"""A remote zip or tar read with HTTP Range requests, member by member.

Public 3D datasets are often one big archive on S3 or Zenodo: KITTI raw
drives (459 MB zip), the Medical Segmentation Decathlon tasks (tar),
AMOS 22 (24 GB zip64). Downloading the whole file to look at one scan is
the thing this source avoids. Measured 2026-10: the zip central directory
of a 459 MB KITTI drive costs 157 KB; the 61 tar headers of MSD Task02
cost 32 KB; the 1 207-entry central directory of AMOS costs 145 KB. One
member then costs its own size.

The index is cached on disk next to the extracted members. When the
server does not honour ranges, the archive is downloaded once (checksum
verified when the manifest gives one) and read locally.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import tarfile
import tempfile
import zipfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from loguru import logger

from ...errors import FetchError
from ..cache import dataset_cache_dir

__all__ = ["RemoteArchiveSource", "RemoteTar", "RemoteZip"]

_INDEX_NAME = ".pardesline-archive-index.json"
_TIMEOUT = 120


@dataclass(frozen=True)
class Member:
    name: str
    offset: int  # of the data (zip: local header; tar: header block)
    size: int  # uncompressed
    csize: int = 0  # compressed (zip)
    method: int = 0  # zip compression method
    crc32: int | None = None


class _Ranged:
    """GET with Range, counting bytes; detects servers that ignore ranges."""

    def __init__(self, url: str, client: httpx.Client):
        self.url = url
        self.client = client
        self.bytes_read = 0
        self.size: int | None = None
        self.supports_ranges: bool | None = None

    def probe(self) -> None:
        try:
            r = self.client.get(self.url, headers={"Range": "bytes=0-0"})
        except httpx.HTTPError as exc:
            raise FetchError(f"cannot reach {self.url}: {exc}") from None
        if r.status_code == 206:
            self.supports_ranges = True
            cr = r.headers.get("content-range", "")
            self.size = int(cr.rsplit("/", 1)[-1]) if "/" in cr else None
        elif r.status_code == 200:
            self.supports_ranges = False
            self.size = int(r.headers.get("content-length") or 0) or None
            r.close()
        else:
            raise FetchError(f"HTTP {r.status_code} for {self.url}")
        if self.size is None:
            try:
                h = self.client.head(self.url)
                self.size = int(h.headers.get("content-length") or 0) or None
            except httpx.HTTPError:
                pass
        if self.size is None:
            raise FetchError(f"{self.url}: the server does not tell the archive size.")

    def get(self, start: int, length: int) -> bytes:
        if length <= 0:
            return b""
        try:
            r = self.client.get(self.url, headers={"Range": f"bytes={start}-{start + length - 1}"})
        except httpx.HTTPError as exc:
            raise FetchError(f"range request failed on {self.url}: {exc}") from None
        if r.status_code != 206:
            raise FetchError(f"{self.url}: expected a partial response, got HTTP {r.status_code}")
        self.bytes_read += len(r.content)
        return r.content


class RemoteZip:
    """Index: end-of-central-directory (+ zip64) then the central directory."""

    def __init__(self, ranged: _Ranged):
        self.r = ranged

    def index(self) -> list[Member]:
        size = self.r.size or 0
        tail_len = min(size, 66_000)
        tail = self.r.get(size - tail_len, tail_len)
        i = tail.rfind(b"PK\x05\x06")
        if i < 0:
            raise FetchError("not a zip archive (no end-of-central-directory record)")
        n_entries, cd_size, cd_offset = struct.unpack("<HII", tail[i + 10 : i + 20])
        if cd_offset == 0xFFFFFFFF or n_entries == 0xFFFF or cd_size == 0xFFFFFFFF:
            j = tail.rfind(b"PK\x06\x06")
            if j < 0:
                raise FetchError("zip64 archive without a zip64 end-of-central-directory record")
            n_entries, cd_size, cd_offset = struct.unpack("<QQQ", tail[j + 32 : j + 56])
        cd = self.r.get(cd_offset, cd_size)
        members: list[Member] = []
        p = 0
        while p + 46 <= len(cd) and cd[p : p + 4] == b"PK\x01\x02":
            method = struct.unpack("<H", cd[p + 10 : p + 12])[0]
            crc, csize, usize, nlen, xlen, clen = struct.unpack("<IIIHHH", cd[p + 16 : p + 34])
            lho = struct.unpack("<I", cd[p + 42 : p + 46])[0]
            name = cd[p + 46 : p + 46 + nlen].decode("utf-8", "replace")
            if 0xFFFFFFFF in (usize, csize, lho):
                extra, q = cd[p + 46 + nlen : p + 46 + nlen + xlen], 0
                while q + 4 <= len(extra):
                    hid, hlen = struct.unpack("<HH", extra[q : q + 4])
                    if hid == 0x0001:
                        vals, k = [], q + 4
                        for cur in (usize, csize, lho):
                            if cur == 0xFFFFFFFF:
                                vals.append(struct.unpack("<Q", extra[k : k + 8])[0])
                                k += 8
                            else:
                                vals.append(cur)
                        usize, csize, lho = vals
                        break
                    q += 4 + hlen
            if not name.endswith("/"):
                members.append(Member(name, lho, usize, csize, method, crc))
            p += 46 + nlen + xlen + clen
        if not members:
            raise FetchError("the zip archive lists no file")
        return members

    def read(self, m: Member) -> bytes:
        hdr = self.r.get(m.offset, 30)
        if hdr[:4] != b"PK\x03\x04":
            raise FetchError(f"{m.name}: local header not found where the central directory says")
        nlen, xlen = struct.unpack("<HH", hdr[26:30])
        data = self.r.get(m.offset + 30 + nlen + xlen, m.csize)
        if m.method == 0:
            out = data
        elif m.method == 8:
            out = zlib.decompress(data, -15)
        else:
            raise FetchError(f"{m.name}: unsupported zip compression method {m.method}")
        if m.crc32 is not None and (zlib.crc32(out) & 0xFFFFFFFF) != m.crc32:
            raise FetchError(f"{m.name}: CRC mismatch after download")
        return out


class RemoteTar:
    """Index: walk the 512-byte headers, skipping each member's data (one
    small request per member; uncompressed tar only)."""

    def __init__(self, ranged: _Ranged):
        self.r = ranged

    @staticmethod
    def _octal(b: bytes) -> int:
        s = b.split(b"\0", 1)[0].strip()
        if not s:
            return 0
        if s[0] & 0x80:  # GNU base-256
            return int.from_bytes(s, "big") & ((1 << (8 * len(s) - 1)) - 1)
        return int(s, 8)

    def index(self) -> list[Member]:
        size = self.r.size or 0
        off = 0
        members: list[Member] = []
        pending_name: str | None = None
        while off + 512 <= size:
            hdr = self.r.get(off, 512)
            if hdr[:1] == b"\0":
                break
            name = hdr[0:100].split(b"\0", 1)[0].decode("utf-8", "replace")
            msize = self._octal(hdr[124:136])
            typ = hdr[156:157]
            prefix = (
                hdr[345:500].split(b"\0", 1)[0].decode("utf-8", "replace") if hdr[257:262] == b"ustar" else ""
            )
            data_off = off + 512
            off = data_off + ((msize + 511) // 512) * 512
            if typ == b"L":  # GNU long name: the data block holds the real name
                pending_name = self.r.get(data_off, msize).split(b"\0", 1)[0].decode("utf-8", "replace")
                continue
            if typ in (b"K", b"x", b"g"):  # long link / pax headers: skip
                continue
            full = pending_name or ((prefix + "/" + name) if prefix else name)
            pending_name = None
            if typ in (b"0", b"\0", b"7"):
                members.append(Member(full, data_off, msize))
        if not members:
            raise FetchError(
                "the tar archive lists no regular file (compressed tars cannot be read by range)"
            )
        return members

    def read(self, m: Member) -> bytes:
        return self.r.get(m.offset, m.size)


class RemoteArchiveSource:
    """``Source`` over one remote archive; members are extracted on demand
    into the dataset cache. ``prefix`` restricts the listing."""

    def __init__(
        self,
        name: str,
        url: str,
        *,
        format: str,
        prefix: str | None = None,
        sha512: str | None = None,
        md5: str | None = None,
        cache: Path | None = None,
    ):
        if format not in ("zip", "tar"):
            raise FetchError(f"unsupported archive format {format!r}; zip or uncompressed tar")
        self.name = name
        self.url = url
        self.format = format
        self.prefix = prefix.strip("/") + "/" if prefix else ""
        self.sha512 = sha512
        self.md5 = md5
        self.cache = cache if cache is not None else dataset_cache_dir(name)
        self._members: dict[str, Member] | None = None
        self._client: httpx.Client | None = None
        self._ranged: _Ranged | None = None
        self._local: Path | None = None  # the whole archive, when ranges are not supported

    # ---- plumbing ---------------------------------------------------------
    def _open(self) -> _Ranged:
        if self._ranged is None:
            self._client = httpx.Client(follow_redirects=True, timeout=_TIMEOUT)
            self._ranged = _Ranged(self.url, self._client)
            self._ranged.probe()
        return self._ranged

    def _index_path(self) -> Path:
        return self.cache / _INDEX_NAME

    def _members_dict(self) -> dict[str, Member]:
        if self._members is not None:
            return self._members
        idx = self._index_path()
        if idx.is_file():
            try:
                data = json.loads(idx.read_text(encoding="utf-8"))
                if data.get("url") == self.url:
                    self._members = {m["name"]: Member(**m) for m in data["members"]}
                    return self._members
            except (OSError, ValueError, TypeError):
                pass
        r = self._open()
        if not r.supports_ranges:
            logger.info("{}: no Range support; downloading the whole archive once", self.url)
            members = self._index_local(self._download_whole())
        else:
            reader = RemoteZip(r) if self.format == "zip" else RemoteTar(r)
            members = reader.index()
            logger.debug(
                "{}: indexed {} members using {:.0f} KB of {:.0f} MB",
                self.name,
                len(members),
                r.bytes_read / 1e3,
                (r.size or 0) / 1e6,
            )
        self._members = {m.name: m for m in members}
        try:
            idx.parent.mkdir(parents=True, exist_ok=True)
            idx.write_text(
                json.dumps({"url": self.url, "size": r.size, "members": [asdict(m) for m in members]}),
                encoding="utf-8",
            )
        except OSError as exc:  # pragma: no cover
            logger.debug("index not cached: {}", exc)
        return self._members

    def _download_whole(self) -> Path:
        if self._local is not None and self._local.is_file():
            return self._local
        target = self.cache / ("archive." + self.format)
        if not target.is_file():
            assert self._client is not None
            h512, hmd5 = hashlib.sha512(), hashlib.md5()
            fd, tmp_name = tempfile.mkstemp(prefix="pardesline-", dir=self.cache)
            tmp = Path(tmp_name)
            try:
                with open(fd, "wb") as out, self._client.stream("GET", self.url) as resp:
                    if resp.status_code != 200:
                        raise FetchError(f"HTTP {resp.status_code} for {self.url}")
                    for chunk in resp.iter_bytes(1 << 20):
                        out.write(chunk)
                        h512.update(chunk)
                        hmd5.update(chunk)
            except (httpx.HTTPError, OSError) as exc:
                tmp.unlink(missing_ok=True)
                raise FetchError(str(exc)) from None
            if (self.sha512 and h512.hexdigest() != self.sha512) or (
                self.md5 and hmd5.hexdigest() != self.md5
            ):
                tmp.unlink(missing_ok=True)
                raise FetchError("checksum mismatch - the archive is not the one the manifest describes")
            shutil.move(str(tmp), target)
        self._local = target
        return target

    def _index_local(self, archive: Path) -> list[Member]:
        if self.format == "zip":
            with zipfile.ZipFile(archive) as zf:
                return [
                    Member(i.filename, i.header_offset, i.file_size, i.compress_size, i.compress_type, i.CRC)
                    for i in zf.infolist()
                    if not i.is_dir()
                ]
        with tarfile.open(archive) as tf:
            return [Member(m.name, m.offset_data, m.size) for m in tf.getmembers() if m.isfile()]

    def _read_local(self, m: Member) -> bytes:
        archive = self._download_whole()
        if self.format == "zip":
            with zipfile.ZipFile(archive) as zf:
                return zf.read(m.name)
        with tarfile.open(archive) as tf:
            fp = tf.extractfile(m.name)
            if fp is None:
                raise FetchError(f"{m.name}: not a file in the archive")
            return fp.read()

    # ---- Source protocol --------------------------------------------------
    def list(self) -> list[str]:
        names = sorted(self._members_dict())
        if self.prefix:
            names = [n for n in names if n.startswith(self.prefix)]
        # AppleDouble / Finder noise that macOS-made archives drag along
        return [n for n in names if not Path(n).name.startswith("._") and Path(n).name != ".DS_Store"]

    def fetch(self, relpath: str) -> Path:
        members = self._members_dict()
        if relpath not in members:
            raise FetchError(f"{relpath!r} is not a member of {self.url}")
        m = members[relpath]
        target = self.cache / relpath
        if target.is_file() and target.stat().st_size == m.size:
            return target
        r = self._open()
        if r.supports_ranges:
            reader = RemoteZip(r) if self.format == "zip" else RemoteTar(r)
            data = reader.read(m)
        else:
            data = self._read_local(m)
        if len(data) != m.size:
            raise FetchError(f"{relpath}: got {len(data)} bytes, the archive index says {m.size}")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        tmp.write_bytes(data)
        tmp.replace(target)
        logger.info("{}: fetched {} ({:.1f} MB) from the remote archive", self.name, relpath, m.size / 1e6)
        return target

    def describe(self) -> str:
        return f"remote {self.format} {self.url}, members cached in {self.cache}"
