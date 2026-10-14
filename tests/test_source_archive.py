"""Remote zip / tar archives read by HTTP Range against a local server."""

from __future__ import annotations

import hashlib
import io
import tarfile
import threading
import zipfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import pytest

import pardesline as pl
from pardesline.data.manifest import Manifest
from pardesline.data.sources.archive import RemoteArchiveSource


class _RangeHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler plus a minimal Range implementation."""

    def log_message(self, *a, **k):
        pass

    def do_GET(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        try:
            with open(path, "rb") as fp:
                data = fp.read()
        except OSError:
            self.send_error(404)
            return
        if rng and rng.startswith("bytes=") and getattr(self.server, "ranges", True):
            start, end = rng[6:].split("-")
            start, end = int(start), int(end) if end else len(data) - 1
            chunk = data[start : end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{start + len(chunk) - 1}/{len(data)}")
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            self.wfile.write(chunk)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(_RangeHandler, directory=str(root)))
    httpd.ranges = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{httpd.server_address[1]}", httpd
    httpd.shutdown()


MEMBERS = {
    "drive/velodyne/0000000000.bin": np.arange(8, dtype=np.float32).tobytes(),
    "drive/velodyne/0000000001.bin": np.arange(16, dtype=np.float32).tobytes(),
    "drive/image/0000000000.png": b"\x89PNG" + b"\0" * 50,
    "drive/._junk.bin": b"apple",
    "other/readme.txt": b"hello",
}


def _zip(deflate: bool) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED if deflate else zipfile.ZIP_STORED) as zf:
        for name, data in MEMBERS.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in MEMBERS.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _manifest(url, fmt, tmp_path, **source_extra):
    m = Manifest.from_dict(
        {
            "name": "drive",
            "source": {"scheme": "archive", "url": url, "format": fmt, "prefix": "drive", **source_extra},
            "license": {"spdx": "CC0-1.0"},
            "roles": {
                "lidar": {
                    "type": "points",
                    "pattern": "drive/velodyne/{frame}.bin",
                    "layout": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "r"]},
                    "frame": "sensor",
                    "units": "m",
                },
                "image": {"type": "image", "pattern": "drive/image/{frame}.png"},
            },
        }
    )
    return m.save(tmp_path / f"drive_{fmt}.json")


@pytest.mark.parametrize("fmt,deflate", [("zip", True), ("zip", False), ("tar", False)])
def test_members_by_range(server, tmp_path, fmt, deflate):
    root, base, _httpd = server
    blob = _zip(deflate) if fmt == "zip" else _tar()
    (root / f"a.{fmt}").write_bytes(blob)
    pl.set_cache_dir(tmp_path / "cache")
    try:
        ds = pl.load(_manifest(f"{base}/a.{fmt}", fmt, tmp_path))
        assert ds.ids == ["0000000000", "0000000001"]  # prefix applied, AppleDouble member dropped
        assert ds["0000000000"].roles == ["lidar", "image"] and ds["0000000001"].roles == ["lidar"]
        src: RemoteArchiveSource = ds._source
        cloud = ds["0000000001"].lidar
        assert cloud.to_numpy().shape == (4, 3)
        assert src._ranged and src._ranged[0].supports_ranges is True
        assert not (
            tmp_path / "cache" / "datasets" / "drive" / f"archive.{fmt}"
        ).exists()  # never downloaded whole
        assert (tmp_path / "cache" / "datasets" / "drive" / ".pardesline-archive-index.json").is_file()
        assert ds["0000000000"].path("lidar").read_bytes() == MEMBERS["drive/velodyne/0000000000.bin"]
        # a second dataset over the same archive reuses the on-disk index: no probe needed to list
        ds2 = pl.load(_manifest(f"{base}/a.{fmt}", fmt, tmp_path))
        assert ds2._source._ranged == {} and ds2.ids == ds.ids
        with pytest.raises(pl.FetchError, match="not a member"):
            src.fetch("nope.bin")
    finally:
        pl.set_cache_dir(None)


def test_whole_download_when_server_ignores_ranges(server, tmp_path):
    root, base, httpd = server
    httpd.ranges = False
    blob = _zip(True)
    (root / "a.zip").write_bytes(blob)
    pl.set_cache_dir(tmp_path / "cache")
    try:
        bad = _manifest(f"{base}/a.zip", "zip", tmp_path, sha512="0" * 128)
        with pytest.raises(pl.FetchError, match="checksum mismatch"):
            _ = pl.load(bad).ids
        good = _manifest(f"{base}/a.zip", "zip", tmp_path, sha512=hashlib.sha512(blob).hexdigest())
        ds = pl.load(good)
        assert ds.ids == ["0000000000", "0000000001"]
        assert ds[0].lidar.to_numpy().shape == (2, 3)
        assert (tmp_path / "cache" / "datasets" / "drive" / "archive.zip").is_file()
    finally:
        pl.set_cache_dir(None)


def test_format_inferred_or_required():
    m = Manifest.from_dict(
        {
            "name": "x",
            "source": {"scheme": "archive", "url": "https://h/a.zip"},
            "roles": {"r": {"type": "file", "pattern": "{id}.txt"}},
        }
    )
    assert m.source.archive_format == "zip"
    with pytest.raises(pl.ManifestError, match=r"source\.format"):
        Manifest.from_dict(
            {
                "name": "x",
                "source": {"scheme": "archive", "url": "https://h/a.tar.gz"},
                "roles": {"r": {"type": "file", "pattern": "{id}.txt"}},
            }
        )
