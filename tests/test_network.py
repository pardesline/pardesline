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


@pytest.mark.medical
def test_msd_heart_tar_by_range():
    ds = pl.load("msd_task02_heart")
    assert len(ds) == 30 and len(ds.filter(split="Tr")) == 20
    s = ds.filter(split="Tr")[0]
    mask = s.mask
    assert isinstance(mask, pl.LabelMap) and mask.labels == {1: "left_atrium"} and mask.frame.axes == "LPS"
    src = ds._source
    assert src._ranged is None or src._ranged.supports_ranges  # indexed from cache or by Range


def test_kitti_raw_bin_through_layout():
    ds = pl.load("kitti_raw_2011_09_26_drive_0001")
    assert len(ds) >= 108
    sweep = ds["0000000000"].lidar
    assert isinstance(sweep, pl.PointCloud) and sweep.units == "m"
    xyz = sweep.to_numpy()
    assert xyz.shape[1] == 3 and 50_000 < xyz.shape[0] < 200_000


def test_hf_nsclc_listing_and_one_mask():
    pytest.importorskip("huggingface_hub")
    ds = pl.load("hf_nsclc_radiomics")
    assert len(ds) == 422
    mask = ds["LUNG1-001"].mask
    assert isinstance(mask, pl.LabelMap) and mask.labels[2] == "gtv"
