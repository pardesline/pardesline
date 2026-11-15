"""I-8: every bundled manifest says exactly which data it loads, or is listed as knowingly unpinned."""

from __future__ import annotations

import threading
from functools import partial
from http.server import ThreadingHTTPServer

import pytest
from test_source_archive import _RangeHandler, _zip

import pardesline as pl
from pardesline.data.manifest import Manifest
from pardesline.data.pinning import KNOWINGLY_UNPINNED, pin_status


def test_every_bundled_manifest_is_pinned_or_listed_with_a_reason():
    unexplained = []
    for m in pl.datasets():
        pinned, how = pin_status(m)
        if not pinned and len(KNOWINGLY_UNPINNED.get(m.name, "").split()) < 5:
            unexplained.append(f"{m.name}: {how}")
    assert not unexplained, "unpinned manifests without a reason:\n" + "\n".join(unexplained)


def test_the_unpinned_list_has_no_stale_entry():
    names = {m.name: m for m in pl.datasets()}
    stale = [n for n in KNOWINGLY_UNPINNED if n not in names or pin_status(names[n])[0]]
    assert not stale, f"listed as unpinned but missing or now pinned: {stale}"


def _manifest(source: dict) -> Manifest:
    return Manifest.model_validate(
        {
            "name": "new_dataset",
            "title": "t",
            "description": "d",
            "citation": "c",
            "license": {"spdx": "CC-BY-4.0", "source_url": "https://example.org"},
            "source": source,
            "roles": {"image": {"type": "volume", "pattern": "{id}.nii.gz"}},
        }
    )


@pytest.mark.parametrize(
    "source",
    [
        {"scheme": "hf", "repo_id": "org/new"},
        {"scheme": "hf", "repo_id": "org/new", "revision": "v1.0"},
        {"scheme": "archive", "url": "https://example.org/a.zip"},
    ],
)
def test_a_new_unpinned_source_is_caught(source):
    m = _manifest(source)
    assert m.name not in KNOWINGLY_UNPINNED
    assert pin_status(m)[0] is False


def test_pinned_sources_pass():
    assert pin_status(_manifest({"scheme": "hf", "repo_id": "org/new", "revision": "a" * 40}))[0]
    url = "https://example.org/a.zip"
    assert pin_status(_manifest({"scheme": "archive", "url": url, "pins": {url: {"size_bytes": 10}}}))[0]


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(_RangeHandler, directory=str(root)))
    httpd.ranges = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_an_archive_that_changed_since_it_was_pinned_is_refused(server, tmp_path):
    from pardesline.data.sources.archive import RemoteArchiveSource

    root, base = server
    blob = _zip(False)
    (root / "a.zip").write_bytes(blob)
    url = f"{base}/a.zip"
    ok = RemoteArchiveSource(
        "d1", url, format="zip", cache=tmp_path / "c1", pins={url: {"size_bytes": len(blob)}}
    )
    assert ok._open(0).size == len(blob)
    bad = RemoteArchiveSource(
        "d2",
        url,
        format="zip",
        cache=tmp_path / "c2",
        pins={url: {"size_bytes": len(blob) + 1, "checked": "2026-11-15"}},
    )
    with pytest.raises(pl.FetchError, match="archive changed"):
        bad._open(0)
