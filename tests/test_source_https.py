"""The https source against a local HTTP server: hashes, mirrors, archives, cache."""

from __future__ import annotations

import hashlib
import io
import tarfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

import pardesline as pl
from pardesline.data.manifest import FileSpec, Manifest
from pardesline.data.sources.https import HttpsSource


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a, **k: None  # type: ignore[attr-defined]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield root, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _sha(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def test_fetch_verify_cache(server, tmp_path):
    root, base = server
    payload = b"ply\nformat ascii 1.0\n"
    (root / "a.ply").write_bytes(payload)
    src = HttpsSource(
        "t", {"a.ply": FileSpec(sha512=_sha(payload), url=f"{base}/a.ply")}, cache=tmp_path / "cache"
    )
    p = src.fetch("a.ply")
    assert p.read_bytes() == payload and p == tmp_path / "cache" / "a.ply"
    # second fetch comes from the cache (the served file is changed, not deleted: on Windows the
    # server thread may still hold it open and unlink would raise PermissionError)
    (root / "a.ply").write_bytes(b"changed on the server")
    assert src.fetch("a.ply") == p
    p.write_bytes(b"corrupted")  # a tampered cache entry is re-downloaded (and fails here: server file gone)
    with pytest.raises(pl.FetchError, match="could not fetch"):
        src.fetch("a.ply")


def test_hash_mismatch_is_refused(server, tmp_path):
    root, base = server
    (root / "a.ply").write_bytes(b"something else")
    src = HttpsSource(
        "t", {"a.ply": FileSpec(sha512=_sha(b"expected"), url=f"{base}/a.ply")}, cache=tmp_path / "cache"
    )
    with pytest.raises(pl.FetchError, match="SHA-512 mismatch"):
        src.fetch("a.ply")
    assert not list((tmp_path / "cache").glob("*.ply"))


def test_mirrors_by_hash(server, tmp_path):
    root, base = server
    payload = b"volume bytes"
    h = _sha(payload)
    (root / "SHA512").mkdir()
    (root / "SHA512" / h).write_bytes(payload)
    src = HttpsSource(
        "t",
        {"vol.mha": FileSpec(sha512=h)},
        mirrors=[f"{base}/missing/{{sha512}}", f"{base}/SHA512/{{sha512}}"],
        cache=tmp_path / "cache",
    )
    assert src.fetch("vol.mha").read_bytes() == payload


def test_archive_members_land_next_to_the_declared_path(server, tmp_path):
    root, base = server
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in (("00-P.mhd", b"ObjectType = Image\n"), ("00-P.raw", b"\0" * 64)):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    archive = buf.getvalue()
    (root / "00.tar").write_bytes(archive)
    src = HttpsSource(
        "t",
        {"POPI/meta/00-P.mhd": FileSpec(sha512=_sha(archive), url=f"{base}/00.tar", archive=True)},
        cache=tmp_path / "cache",
    )
    p = src.fetch("POPI/meta/00-P.mhd")
    assert p.is_file() and p.with_suffix(".raw").is_file() and p.parent.name == "meta"
    assert src.fetch("POPI/meta/00-P.mhd") == p  # archive members are not re-hashed


def test_undeclared_file(tmp_path):
    src = HttpsSource("t", {}, cache=tmp_path)
    with pytest.raises(pl.FetchError, match="not declared"):
        src.fetch("x.ply")


def test_dataset_over_https(server, tmp_path, monkeypatch):
    root, base = server
    payload = b"\0" * 10
    (root / "a.vti").write_bytes(payload)
    m = Manifest.from_dict(
        {
            "name": "tiny",
            "source": {
                "scheme": "https",
                "files": {"a.vti": {"sha512": _sha(payload), "url": f"{base}/a.vti"}},
            },
            "license": {"spdx": "CC0-1.0"},
            "roles": {"ct": {"type": "volume", "units": "mm", "frame": "LPS"}},
            "samples": [{"id": "s", "files": {"ct": "a.vti"}}],
        }
    )
    pl.set_cache_dir(tmp_path / "cache")
    try:
        path = m.save(tmp_path / "tiny.json")
        ds = pl.load(path)
        obj = ds[0].ct
        assert obj.path.read_bytes() == payload and obj.frame.describe() == "LPS, mm (manifest)"
        assert obj.license.spdx == "CC0-1.0"
        assert ds.fetch_all() == 1
    finally:
        pl.set_cache_dir(None)
