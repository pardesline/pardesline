"""pl.o3d / pl.pv / pl.sitk without the library: nothing leaves the machine unless the user signed in
to the platform; then the 0.1.x cloud mirror, announced in the log."""

from __future__ import annotations

import importlib

import httpx
import pytest

import pardesline as pl
from pardesline.errors import MissingDependency

_real_import = importlib.import_module


@pytest.fixture
def no_open3d(monkeypatch, tmp_path):
    def fake_import(name, *args, **kwargs):
        if name == "open3d":
            raise ImportError("No module named 'open3d'")
        return _real_import(name, *args, **kwargs)

    def no_network(*args, **kwargs):
        raise AssertionError("pl.o3d sent a request without the user signing in")

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(httpx.Client, "request", no_network)
    monkeypatch.delenv("PARDESLINE_API_KEY", raising=False)
    monkeypatch.setenv("PARDESLINE_TOKEN_PATH", str(tmp_path / "no-token"))


def test_missing_library_without_sign_in_fails_locally(no_open3d):
    o3d = pl.o3d
    assert hasattr(pl, "o3d")  # introspection still works
    assert "pardesline[local]" in repr(o3d)
    with pytest.raises(MissingDependency, match=r"open3d is not installed.*pardesline\[local\]"):
        o3d.io.read_point_cloud("scan.ply")
    with pytest.raises(MissingDependency):
        o3d()


def test_missing_library_with_a_platform_key_uses_the_cloud_mirror(no_open3d, monkeypatch):
    monkeypatch.setenv("PARDESLINE_API_KEY", "pl_test")
    from pardesline import cloud

    mirror = pl.o3d
    assert mirror is not None and type(mirror).__module__.startswith("pardesline.cloud")
    assert type(mirror) is type(cloud.o3d)
