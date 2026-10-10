"""End-to-end runs of representative algorithms on generated data.
Each test exercises one native library through the real subprocess contract."""

from __future__ import annotations

import json

import numpy as np
import pytest

import pardesline as pl

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def cloud_ply(tmp_path_factory):
    o3d = pytest.importorskip("open3d")
    rng = np.random.default_rng(0)
    pts = rng.normal(size=(4000, 3)).astype(np.float64)
    pts /= np.linalg.norm(pts, axis=1, keepdims=True)  # unit sphere
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts))
    path = tmp_path_factory.mktemp("data") / "sphere.ply"
    o3d.io.write_point_cloud(str(path), pcd)
    return path


@pytest.fixture(scope="module")
def mesh_ply(tmp_path_factory):
    pv = pytest.importorskip("pyvista")
    path = tmp_path_factory.mktemp("data") / "sphere_mesh.ply"
    pv.Sphere(theta_resolution=60, phi_resolution=60).save(str(path))
    return path


@pytest.fixture(scope="module")
def volume_mha(tmp_path_factory):
    sitk = pytest.importorskip("SimpleITK")
    z, y, x = np.mgrid[0:32, 0:32, 0:32]
    arr = (((x - 16) ** 2 + (y - 16) ** 2 + (z - 16) ** 2) < 100).astype(np.float32) * 200 + 10
    img = sitk.GetImageFromArray(arr)
    img.SetSpacing((1.0, 1.0, 1.0))
    path = tmp_path_factory.mktemp("data") / "sphere.mha"
    sitk.WriteImage(img, str(path))
    return path


@pytest.mark.local
def test_point_cloud_chain(cloud_ply, out_dir):
    o3d = pytest.importorskip("open3d")
    scan = pl.load(cloud_ply)
    small = scan.downsample(voxel_size=0.2)
    assert small.kind == "pointcloud" and small.path.parent == out_dir
    assert len(small.provenance) == 1 and small.provenance[0]["params"] == {"voxel_size": "0.2"}
    n_in = len(scan.to_open3d().points)
    n_out = len(small.to_open3d().points)
    assert 0 < n_out < n_in
    clean = small.remove_outliers(nb_neighbors=10, std_ratio=2.0)
    assert len(clean.provenance) == 2
    surf = clean.normals().poisson(depth=5)
    mesh = surf.to_open3d()
    assert isinstance(mesh, o3d.geometry.TriangleMesh) and len(mesh.triangles) > 0


@pytest.mark.local
def test_run_function_with_explicit_output(cloud_ply, tmp_path):
    res = pl.run(
        "point_cloud_processing", "voxel_downsample", cloud_ply, tmp_path / "small.ply", voxel_size=0.3
    )
    assert res.output == tmp_path / "small.ply" and res.output.stat().st_size > 0
    assert res.duration_s > 0 and "voxel" in res.log.lower()
    assert res.sidecar is None


@pytest.mark.local
def test_bad_param_value_fails_before_running(cloud_ply):
    with pytest.raises(pl.ParameterError, match="below the minimum"):
        pl.run("point_cloud_processing", "voxel_downsample", cloud_ply, voxel_size=-1)


@pytest.mark.local
def test_mesh_decimate_and_smooth(mesh_ply, out_dir):
    pv = pytest.importorskip("pyvista")
    mesh = pl.load(mesh_ply)
    out = mesh.decimate(target_reduction=0.5).smooth(n_iterations=10)
    n_in = pv.read(str(mesh_ply)).n_faces_strict
    n_out = out.to_pyvista().n_faces_strict
    assert 0 < n_out < n_in


@pytest.mark.local
def test_registration_writes_sidecar(cloud_ply, out_dir):
    o3d = pytest.importorskip("open3d")
    pcd = o3d.io.read_point_cloud(str(cloud_ply))
    pcd.translate((0.05, -0.02, 0.01))
    moving = out_dir / "moving.ply"
    out_dir.mkdir(exist_ok=True)
    o3d.io.write_point_cloud(str(moving), pcd)
    fixed = pl.load(cloud_ply)
    aligned = fixed.icp(moving, voxel_size=0.05, max_iterations=100)
    assert aligned.registration_sidecar is not None and aligned.transform is not None
    assert aligned.provenance[-1]["moving"] == str(moving)


@pytest.mark.medical
def test_volume_segmentation_and_registration(volume_mha, out_dir):
    sitk = pytest.importorskip("SimpleITK")
    vol = pl.load(volume_mha)
    mask = vol.segment()
    assert mask.kind == "labels" and isinstance(mask, pl.LabelMap)
    arr = sitk.GetArrayFromImage(mask.to_sitk())
    assert arr.max() > 0 and 0 < np.count_nonzero(arr) < arr.size

    img = sitk.ReadImage(str(volume_mha))
    t = sitk.TranslationTransform(3, (2.0, -1.0, 0.5))
    moved = sitk.Resample(img, img, t, sitk.sitkLinear, 10.0, img.GetPixelID())
    moving = out_dir / "moving.mha"
    out_dir.mkdir(exist_ok=True)
    sitk.WriteImage(moved, str(moving))
    reg = vol.register(moving, num_iterations=30, metric="mean_squares")
    assert reg.registration_sidecar is not None
    sidecar = json.loads(reg.path.with_suffix(".json").read_text())
    assert "transform" in json.dumps(sidecar).lower()


@pytest.mark.medical
def test_medical_api_imports():
    from pardesline import medical

    assert callable(medical.load_volume) and callable(medical.register_rigid)


@pytest.mark.medical
@pytest.mark.local
def test_volume_frame_segment_and_exact_mesh(volume_mha, out_dir):
    """Header → frame; threshold → LabelMap; label → exact surface in mm."""
    vol = pl.load(volume_mha)
    assert isinstance(vol, pl.Volume) and vol.frame.describe() == "LPS, mm (file)"
    assert vol.info()["size"] == (32, 32, 32) and vol.frame.affine[0][0] == 1.0
    mask = vol.segment(lower=100, upper=300)
    assert isinstance(mask, pl.LabelMap) and mask.labels == {1: "foreground"}
    assert mask.frame.axes == "LPS" and mask.license is vol.license
    surf = mask.to_mesh()
    assert isinstance(surf, pl.Mesh) and surf.units == "mm"
    step = surf.provenance[-1]
    assert step["op"] == "volume_to_mesh" and step["exact"] and step["label"] == 1 and step["n_faces"] > 100
    pv_mesh = surf.to_pyvista()
    center = pv_mesh.center
    assert all(abs(c - 16.0) < 1.5 for c in center)  # sphere centred at voxel (16,16,16), spacing 1 mm
    radius = ((pv_mesh.points - center) ** 2).sum(axis=1) ** 0.5
    assert 8.5 < radius.mean() < 11.0  # radius ~10 voxels
    with pytest.raises(ValueError, match="exactly one"):
        vol.to_mesh()
    iso = vol.to_mesh(isovalue=100.0)
    assert iso.provenance[-1]["exact"] is False
