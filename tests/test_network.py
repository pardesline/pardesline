"""Real downloads of the bundled datasets. Off by default:
``PARDESLINE_NETWORK_TESTS=1 pytest tests/test_network.py``."""

from __future__ import annotations

import os

import pytest

import pardesline as pl

pytestmark = [
    pytest.mark.network,
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("PARDESLINE_NETWORK_TESTS"), reason="set PARDESLINE_NETWORK_TESTS=1"
    ),
]


@pytest.mark.medical
def test_rire_brain_downloads_and_registers():
    ds = pl.load("rire_brain")
    s = ds[0]
    assert s.roles == ["ct", "mr_t1"]
    ct = s.ct
    assert ct.frame.describe() == "LPS, mm (file)" and ct.info()["size"] == (512, 512, 29)
    moved = ct.align(s.mr_t1, num_iterations=20, metric="mattes_mutual_information")
    assert moved.transform is not None and moved.provenance[-1]["step"] == "run"


@pytest.mark.medical
def test_liver_labels_to_mesh():
    ds = pl.load("liver_tumor_patient01")
    s = ds[0]
    rad = s.rad01
    assert isinstance(rad, pl.LabelMap) and rad.labels == {1: "tumor"}
    surf = rad.to_mesh()  # single label → default
    assert surf.kind == "mesh" and surf.provenance[-1]["exact"] is True and surf.units == "mm"


@pytest.mark.local
def test_open3d_bunny():
    ds = pl.load("open3d_bunny")
    mesh = ds[0].mesh
    assert mesh.kind == "mesh" and mesh.units == "m"
    pts = mesh.to_points(num_points=2000)
    assert pts.kind == "pointcloud" and pts.license.source_url
