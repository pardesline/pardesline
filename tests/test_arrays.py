"""Raw arrays (.npy / .npz / .bin) read through a declared layout, never guessed."""

from __future__ import annotations

import numpy as np
import pytest

import pardesline as pl
from pardesline.object import arrays


def _read_ply_header(path):
    with open(path, "rb") as fp:
        head = b""
        while not head.endswith(b"end_header\n"):
            head += fp.readline()
    return head.decode()


def test_bin_points_need_layout(tmp_path):
    pts = np.array([[0, 0, 0, 0.1], [1, 0, 0, 0.5], [0, 1, 0, 0.9]], dtype=np.float32)
    f = tmp_path / "sweep.bin"
    pts.tofile(f)
    raw = pl.load(f)
    assert isinstance(raw, pl.RawArray) and raw.kind == "array" and raw.is_raw_array
    with pytest.raises(pl.ManifestError, match="needs a layout"):
        raw.to_numpy()
    with pytest.raises(pl.ParameterError, match="unknown kind"):
        raw._op_input()
    cloud = raw.as_points(dtype="float32", shape="(N,4)", columns=["x", "y", "z", "reflectance"])
    assert isinstance(cloud, pl.PointCloud) and cloud.layout["dtype"] == "float32"
    assert cloud.to_numpy().shape == (3, 3) and cloud.units is None  # frame still unknown
    ply = cloud._op_input()
    assert ply.suffix == ".ply" and cloud._op_extension() == ".ply"
    head = _read_ply_header(ply)
    assert "element vertex 3" in head and "property float reflectance" in head
    assert cloud._op_input() == ply  # materialised once


def test_load_with_layout_picks_points_or_grid(tmp_path):
    f = tmp_path / "pts.npy"
    np.save(f, np.random.rand(10, 3).astype(np.float32))
    obj = pl.load(f, layout={"shape": "(N,3)", "columns": ["x", "y", "z"]})
    assert isinstance(obj, pl.PointCloud)
    g = tmp_path / "grid.npy"
    np.save(g, np.zeros((4, 5, 6), dtype=np.uint8))
    vol = pl.load(g, layout={"shape": "(4,5,6)"})
    assert isinstance(vol, pl.Volume) and vol.kind == "volume"
    lab = pl.load(g, layout={"shape": "(4,5,6)"}, kind="labels")
    assert isinstance(lab, pl.LabelMap)
    with pytest.raises(pl.ManifestError, match="kind="):
        pl.load(g, kind="banana")


def test_layout_mismatch_is_refused(tmp_path):
    f = tmp_path / "pts.npy"
    np.save(f, np.random.rand(10, 3).astype(np.float32))
    with pytest.raises(pl.ManifestError, match="does not match"):
        arrays.load_array(f, {"shape": "(N,4)"})
    with pytest.raises(pl.ManifestError, match=r"differs from layout\.dtype"):
        arrays.load_array(f, {"shape": "(N,3)", "dtype": "float64"})
    b = tmp_path / "odd.bin"
    np.arange(7, dtype=np.float32).tofile(b)
    with pytest.raises(pl.ManifestError, match="do not split"):
        arrays.load_array(b, {"dtype": "float32", "shape": "(N,4)"})
    with pytest.raises(pl.ManifestError, match=r"layout\.dtype"):
        arrays.load_array(b, {"shape": "(N,4)"})
    with pytest.raises(pl.ManifestError, match="must name x, y and z"):
        arrays.decode_points(f, {"shape": "(N,3)", "columns": ["a", "b", "c"]})
    with pytest.raises(ValueError, match="look like"):  # pydantic ValidationError
        pl.Layout(shape="N,3")


def test_npz_key_and_colours(tmp_path):
    xyz = np.random.rand(5, 3)
    rgb = (np.random.rand(5, 3) * 255).astype(np.uint8)
    f = tmp_path / "pack.npz"
    np.savez(f, coords=xyz, other=np.zeros(2))
    with pytest.raises(pl.ManifestError, match="which 'key'"):
        arrays.load_array(f, {"shape": "(N,3)"})
    assert arrays.load_array(f, {"key": "coords", "shape": "(N,3)"}).shape == (5, 3)
    with pytest.raises(pl.ManifestError, match="no array"):
        arrays.load_array(f, {"key": "nope"})
    out = arrays.write_ply(tmp_path / "c.ply", xyz, {"r": rgb[:, 0], "g": rgb[:, 1], "b": rgb[:, 2]})
    head = _read_ply_header(out)
    assert "property uchar red" in head and "property uchar blue" in head
    # the written record layout matches the header
    body = out.read_bytes()[len(head.encode()) :]
    assert len(body) == 5 * (3 * 8 + 3)


def test_sidecar_keeps_the_layout(tmp_path):
    f = tmp_path / "sweep.bin"
    np.zeros((4, 4), dtype=np.float32).tofile(f)
    cloud = pl.load(f, layout={"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]})
    copy = cloud.with_frame("sensor", "m").save(tmp_path / "out" / "sweep.bin")
    again = pl.load(copy)  # the sidecar says it is points with this layout
    assert isinstance(again, pl.PointCloud) and again.layout["columns"][-1] == "i"
    assert again.frame.describe() == "sensor, m (user)"
    std = cloud.save(tmp_path / "out" / "sweep.ply")  # a standard format: decoded through the layout
    assert std.suffix == ".ply" and "element vertex 4" in _read_ply_header(std)


@pytest.mark.medical
def test_grid_to_volume(tmp_path):
    grid = np.zeros((6, 5, 4), dtype=np.int64)  # (x, y, z) in the layout convention
    grid[1:3, 1:3, 1:3] = 2
    f = tmp_path / "occ.npz"
    np.savez(f, occ_label=grid, mask=np.ones(3))
    lab = pl.load(f).as_volume(labels={2: "car"}, key="occ_label", shape="(6,5,4)", spacing=[0.4, 0.4, 0.4])
    assert isinstance(lab, pl.LabelMap) and lab.labels == {2: "car"}
    mha = lab._op_input()
    assert mha.suffix == ".mha"
    arr = lab.to_numpy()  # SimpleITK (z, y, x)
    assert arr.shape == (4, 5, 6) and int(arr.max()) == 2
    assert lab.info()["spacing"] == (0.4, 0.4, 0.4)


@pytest.mark.local
def test_bin_sweep_runs_a_catalog_op(tmp_path, out_dir):
    rng = np.random.default_rng(0)
    pts = np.hstack([rng.random((500, 3)) * 2, rng.random((500, 1))]).astype(np.float32)
    f = tmp_path / "sweep.bin"
    pts.tofile(f)
    cloud = pl.load(
        f, layout={"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "reflectance"]}
    )
    small = cloud.downsample(voxel_size=0.4)
    assert small.kind == "pointcloud" and small.path.is_file()
    assert small.provenance[-1]["step"] == "run"
    assert len(small.to_open3d().points) < 500
