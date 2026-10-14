"""The Hugging Face source against a fake ``huggingface_hub``: scoped listing,
listing cache, file cap, rate-limit message, hf:// sub-paths, scan of an
un-manifested repo and the four asking modes."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pytest

import pardesline as pl
from pardesline.data.manifest import Manifest

REPO = "acme/scans"
TREE = {
    "README.md": b"---\nlicense: cc-by-4.0\n---\n",
    "raw/p01/scan.bin": np.arange(8, dtype=np.float32).tobytes(),
    "raw/p02/scan.bin": np.arange(12, dtype=np.float32).tobytes(),
    "meshes/a.stl": b"\0" * 10,
    "meshes/b.stl": b"\0" * 10,
    "huge/" + "x" * 5 + ".ply": b"\0",
}


class _HfError(Exception):
    def __init__(self, status, msg="boom"):
        super().__init__(msg)
        self.response = types.SimpleNamespace(status_code=status)


@pytest.fixture
def fake_hub(monkeypatch, tmp_path):
    """A minimal huggingface_hub: list_repo_tree, hf_hub_download, repo_info, dataset_info."""
    calls = {"tree": [], "download": [], "fail_with": None}
    store = tmp_path / "hubcache"

    class _Entry:
        def __init__(self, path, size=None):
            self.path = path
            self.size = size

    class HfApi:
        def list_repo_tree(self, repo_id, path_in_repo=None, repo_type=None, revision=None, recursive=False):
            calls["tree"].append(path_in_repo)
            if calls["fail_with"]:
                raise _HfError(calls["fail_with"])
            if repo_id != REPO:
                raise _HfError(401, "Repository Not Found")
            for name in sorted(TREE):
                if path_in_repo is None or name.startswith(path_in_repo.rstrip("/") + "/"):
                    yield _Entry(name, len(TREE[name]))
            if path_in_repo is None:
                yield _Entry("raw")  # a folder entry: no size

        def repo_info(self, repo_id, repo_type=None, revision=None):
            if repo_id != REPO:
                raise _HfError(401, "Repository Not Found")
            return types.SimpleNamespace(sha="abc123")

        def dataset_info(self, repo_id):
            card = types.SimpleNamespace(to_dict=lambda: {"license": "cc-by-4.0"})
            return types.SimpleNamespace(card_data=card)

    def hf_hub_download(repo_id, filename, repo_type=None, revision=None):
        calls["download"].append(filename)
        if filename not in TREE:
            raise _HfError(404)
        p = store / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(TREE[filename])
        return str(p)

    mod = types.ModuleType("huggingface_hub")
    mod.HfApi = HfApi
    mod.hf_hub_download = hf_hub_download
    mod.get_token = lambda: None
    utils = types.ModuleType("huggingface_hub.utils")
    utils.HfHubHTTPError = _HfError
    mod.utils = utils
    monkeypatch.setitem(sys.modules, "huggingface_hub", mod)
    monkeypatch.setitem(sys.modules, "huggingface_hub.utils", utils)
    pl.set_cache_dir(tmp_path / "cache")
    yield calls
    pl.set_cache_dir(None)


def _manifest(paths=None, **extra):
    data = {
        "name": "acme_scans",
        "source": {"scheme": "hf", "repo_id": REPO, "paths": paths},
        "license": {"spdx": "CC-BY-4.0"},
        "citation": "n/a",
        "roles": {
            "lidar": {
                "type": "points",
                "pattern": "raw/{id}/scan.bin",
                "layout": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]},
                "frame": "sensor",
                "units": "m",
            },
            "mesh": {"type": "mesh", "pattern": "meshes/{id}.stl", "units": "mm", "frame": "Z-up"},
        },
        **extra,
    }
    return Manifest.from_dict(data)


def test_scoped_listing_is_cached(fake_hub, tmp_path):
    m = _manifest(paths=["raw"])
    path = m.save(tmp_path / "acme.json")
    ds = pl.load(path)
    assert ds.ids == ["p01", "p02"] and fake_hub["tree"] == ["raw"]
    ds2 = pl.load(path)  # second load: listing from the disk cache, no API call
    assert ds2.ids == ["p01", "p02"] and fake_hub["tree"] == ["raw"]
    s = ds["p02"]
    cloud = s.lidar
    assert isinstance(cloud, pl.PointCloud) and cloud.frame.describe() == "sensor, m (manifest)"
    assert cloud.to_numpy().shape == (3, 3) and fake_hub["download"] == ["raw/p02/scan.bin"]
    assert cloud.provenance[0]["source"].startswith("hf://acme/scans@main [raw]")


def test_file_cap_explains_instead_of_429(fake_hub, tmp_path):
    m = _manifest(paths=None, source={"scheme": "hf", "repo_id": REPO, "max_files": 2})
    with pytest.raises(pl.FetchError, match="more than 2 files"):
        pl.load(m.save(tmp_path / "m.json"))


def test_rate_limit_and_not_found_messages(fake_hub, tmp_path):
    m = _manifest(paths=["raw"])
    fake_hub["fail_with"] = 429
    with pytest.raises(pl.FetchError, match="HF_TOKEN"):
        pl.load(m.save(tmp_path / "m.json"))
    fake_hub["fail_with"] = None
    with pytest.raises(pl.FetchError, match="not found"):
        pl.load("hf://nobody/nothing")


def test_hf_subpath_rescopes_a_manifest(fake_hub, tmp_path, monkeypatch):
    m = _manifest(paths=["meshes"])
    monkeypatch.setattr(pl.data, "_bundled", lambda: {m.name: m})
    ds = pl.load(f"hf://{REPO}/raw")
    assert ds.manifest.source.paths == ["raw"] and ds.ids == ["p01", "p02"]
    whole = pl.load(f"hf://{REPO}")
    assert whole.manifest.source.paths == ["meshes"] and whole.ids == ["a", "b"]
    with pytest.raises(pl.ManifestError, match="describes"):
        pl.load(
            f"hf://{REPO}",
            manifest=str(
                _manifest(paths=["raw"])
                .model_copy(
                    update={"source": _manifest().source.model_copy(update={"repo_id": "other/repo"})}
                )
                .save(tmp_path / "other.json")
            ),
        )


def test_unmanifested_repo_is_scanned_and_asks(fake_hub, tmp_path):
    with pytest.raises(pl.NeedsConfirmation) as exc:
        pl.load(f"hf://{REPO}/raw")
    fields = [q.field for q in exc.value.questions]
    assert "license" not in fields  # the Hub card said CC-BY-4.0
    assert "roles.scan.layout" in fields  # raw arrays: type and layout must be declared
    assert exc.value.draft_path and exc.value.draft_path.is_file()
    draft = exc.value.manifest
    assert draft.source.scheme == "hf" and draft.source.paths == ["raw"] and draft.license.spdx == "CC-BY-4.0"
    assert [s.id for s in draft.samples] == ["p01", "p02"]

    ds = pl.load(
        f"hf://{REPO}/raw",
        types={"scan": "points"},
        layout={"scan": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},
        units={"scan": "m"},
        frame={"scan": "sensor"},
    )
    assert not ds.is_draft and ds[0].scan.to_numpy().shape == (2, 3)
    m = pl.scan(f"hf://{REPO}/meshes")
    assert list(m.roles) == ["mesh"] and m.roles["mesh"].type == "mesh" and m.is_draft
    assert any(q.field == "roles.mesh.units" for q in m.questions)


def test_describe_mentions_scope(fake_hub):
    m = _manifest(paths=["raw"])
    assert "hf://acme/scans (raw)" in m.describe()
    assert Path(pl.cache_dir()).is_dir()
