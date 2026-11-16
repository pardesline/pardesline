"""Regression tests for the second batch of the 2026-11-15 audit (design improvements).

"P1-21" = Part 1 entry 21, "P2-Bn" / "P3-Bn" = Part 2 / Part 3 entry Bn. Synthetic data, no network.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

sitk = pytest.importorskip("SimpleITK")


@pytest.mark.medical
@pytest.mark.parametrize("fn_name", ["register_rigid", "register_affine"])
def test_p1_21_default_optimiser_converges_on_simple_cases(fn_name):
    """With plain gradient descent and 1 % sampling, a sphere shifted by (2, -1, 0.5) mm 'registered'
    7.5 m away (exit 0) and blobs rotated 8 degrees ended 5-9 mm off."""
    from _synthetic import blob_volume, moved_copy, tre

    from pardesline.medical import _service as svc

    fn = getattr(svc, fn_name)
    z, y, x = np.mgrid[0:32, 0:32, 0:32]
    sph = sitk.GetImageFromArray(
        (((x - 16) ** 2 + (y - 16) ** 2 + (z - 16) ** 2) < 100).astype(np.float32) * 200 + 10
    )
    shift = sitk.TranslationTransform(3, (2.0, -1.0, 0.5))
    moved = sitk.Resample(sph, sph, shift, sitk.sitkLinear, 10.0, sph.GetPixelID())
    _, tx = fn(sph, moved, metric="mean_squares", num_iterations=30)
    assert tre(tx, shift.GetInverse(), np.array([[16.0, 16.0, 16.0], [10.0, 16.0, 20.0]])) < 0.5

    fixed, pts = blob_volume(size=(48, 48, 40), spacing=(1.5, 1.5, 2.0))
    s_map = sitk.Euler3DTransform(
        (0, 0, 0), math.radians(6), math.radians(-4), math.radians(8), (5.0, -3.0, 4.0)
    )
    _, tx = fn(fixed, moved_copy(fixed, s_map))
    assert tre(tx, s_map.GetInverse(), pts) < 1.0


# ----------------------------------------------------------------------------- shared helpers
def _run(monkeypatch, module, args):
    import importlib
    import sys

    mod = importlib.import_module(module)
    monkeypatch.setattr(sys, "argv", [module, *map(str, args)])
    mod.main()


def _cli(module, args):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, "-m", module, *map(str, args)], capture_output=True, text=True, timeout=600
    )


@pytest.fixture
def sphere_mesh(tmp_path):
    o3d = pytest.importorskip("open3d")
    path = tmp_path / "sphere.ply"
    o3d.io.write_triangle_mesh(str(path), o3d.geometry.TriangleMesh.create_sphere(10.0, 40))
    return path


@pytest.fixture
def sphere_cloud(tmp_path):
    o3d = pytest.importorskip("open3d")
    path = tmp_path / "cloud.ply"
    o3d.utility.random.seed(0)
    pc = o3d.geometry.TriangleMesh.create_sphere(10.0, 60).sample_points_poisson_disk(4000)
    o3d.io.write_point_cloud(str(path), o3d.geometry.PointCloud(pc.points))
    return path


# ----------------------------------------------------------------------------- Part 1
@pytest.mark.medical
@pytest.mark.slow
def test_p1_22_bspline_stage_metric_can_be_mutual_information():
    from _synthetic import blob_volume, moved_copy

    from pardesline.medical import _service as svc

    fixed, _ = blob_volume(size=(32, 32, 32), spacing=(2.0, 2.0, 2.0))
    moving = moved_copy(fixed, sitk.TranslationTransform(3, (1.0, 0.5, 0.0)))
    q: dict = {}
    svc.register_bspline(
        fixed,
        moving,
        grid_spacing=32.0,
        num_iterations=10,
        bspline_metric="mattes_mutual_information",
        quality=q,
    )
    assert "Mattes" in q.get("stop_condition", "") or q.get("iterations") is not None
    with pytest.raises(ValueError, match="bspline_metric"):
        svc.register_bspline(fixed, moving, grid_spacing=32.0, num_iterations=2, bspline_metric="mean_square")


# ----------------------------------------------------------------------------- Part 2
def test_p2_b01_no_false_claim_about_multi_scale_icp():
    from pathlib import Path

    import pardesline.ops.registration.icp_refinement as m

    assert "over-fits" not in Path(m.__file__).read_text(encoding="utf-8")


# ----------------------------------------------------------------------------- Part 3
@pytest.mark.local
def test_p3_b01_a_grid_that_would_exhaust_memory_is_refused(sphere_mesh, tmp_path):
    """voxel_size 0.01 on a 20 mm part asks for billions of nodes: the job exhausted memory."""
    proc = _cli(
        "pardesline.ops.sdf.compute_sdf",
        ["--input", sphere_mesh, "--output", tmp_path / "o.ply", "--voxel_size", 0.04],
    )
    assert proc.returncode == 1 and "nodes" in proc.stderr


@pytest.mark.local
def test_p3_b02_x13_sdf_band_follows_the_grid_and_resolution_is_not_clamped(
    sphere_mesh, tmp_path, monkeypatch
):
    o3d = pytest.importorskip("open3d")
    out = tmp_path / "v.ply"
    _run(
        monkeypatch,
        "pardesline.ops.sdf.sdf_voxel_visualization",
        ["--input", sphere_mesh, "--output", out, "--resolution", 32],
    )
    kept = len(o3d.io.read_point_cloud(str(out)).points)
    assert kept > 2 * 528  # the old +-0.1 band kept 528 of 32 768 nodes
    with pytest.raises(SystemExit) as exc:  # 256 was clamped to 128 without a word
        _run(
            monkeypatch,
            "pardesline.ops.sdf.sdf_voxel_visualization",
            ["--input", sphere_mesh, "--output", tmp_path / "x.ply", "--resolution", 256],
        )
    assert exc.value.code == 1


@pytest.mark.local
def test_p3_b03_alpha_shape_does_not_change_alpha_silently(sphere_cloud, tmp_path, monkeypatch):
    import json

    with pytest.raises(SystemExit) as exc:
        _run(
            monkeypatch,
            "pardesline.ops.point_cloud_reconstruction.alpha_shape",
            ["--input", sphere_cloud, "--output", tmp_path / "a.ply", "--alpha", 0.01],
        )
    assert exc.value.code == 1
    out = tmp_path / "b.ply"
    _run(
        monkeypatch,
        "pardesline.ops.point_cloud_reconstruction.alpha_shape",
        ["--input", sphere_cloud, "--output", out, "--alpha", 0.01, "--auto_retry", "true"],
    )
    rec = json.loads(out.with_suffix(".json").read_text())
    assert rec["retried"] and rec["alpha_used"] > 0.01 and rec["alpha_requested"] == 0.01


@pytest.mark.local
@pytest.mark.slow
def test_p3_b04_poisson_default_keeps_the_surface_closed(sphere_cloud, tmp_path):
    """The default 0.01 density trimming removed vertices and opened a closed sphere; the default
    is now no trimming (Open3D's own surface is kept as reconstructed).

    Run in subprocesses, as the runner does: two Open3D Poisson runs inside the pytest process
    aborted the whole process on macOS CI (2026-11-16)."""
    o3d = pytest.importorskip("open3d")
    default, trimmed = tmp_path / "p.ply", tmp_path / "t.ply"
    module = "pardesline.ops.point_cloud_reconstruction.poisson"
    proc = _cli(module, ["--input", sphere_cloud, "--output", default, "--depth", 7])
    assert proc.returncode == 0, proc.stderr[-2000:]
    proc = _cli(
        module, ["--input", sphere_cloud, "--output", trimmed, "--depth", 7, "--density_quantile", 0.01]
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    n_default = len(o3d.io.read_triangle_mesh(str(default)).vertices)
    n_trimmed = len(o3d.io.read_triangle_mesh(str(trimmed)).vertices)
    assert n_default > n_trimmed


def test_p3_b08_b15_descriptions():
    from pathlib import Path

    import pardesline.ops.pyvista_mesh_processing.smooth_taubin as tau
    import pardesline.ops.voxel_to_mesh.voxelization as vox

    assert "SURFACE" in Path(vox.__file__).read_text(encoding="utf-8")
    assert "volume-preserving" not in Path(tau.__file__).read_text(encoding="utf-8").splitlines()[0]


@pytest.mark.local
def test_p3_b10_glyphs_are_sized_to_the_data(tmp_path, monkeypatch):
    pv = pytest.importorskip("pyvista")
    s = pv.Sphere(radius=10).compute_normals(cell_normals=False)
    s.save(str(tmp_path / "s.vtp"))
    out = tmp_path / "g.vtp"
    _run(
        monkeypatch,
        "pardesline.ops.pyvista_analysis.glyph",
        ["--input", tmp_path / "s.vtp", "--output", out, "--vector_name", "Normals"],
    )
    b = pv.read(str(out)).bounds
    assert b[1] - b[0] > 20.5  # arrows of ~1 unit on a 20-unit sphere (was 0.02)


@pytest.mark.local
def test_p3_b11_threshold_volume_needs_bounds(tmp_path, monkeypatch):
    pv = pytest.importorskip("pyvista")
    g = pv.ImageData(dimensions=(10, 10, 10))
    g.point_data["d"] = np.linspace(-20, 20, 1000).astype(np.float32)
    g.save(str(tmp_path / "d.vti"))
    with pytest.raises(SystemExit) as exc:
        _run(
            monkeypatch,
            "pardesline.ops.pyvista_volume_processing.threshold_volume",
            ["--input", tmp_path / "d.vti", "--output", tmp_path / "o.vtu"],
        )
    assert exc.value.code == 1


@pytest.mark.local
def test_p3_b12_scalar_stats_reports_z_only_when_asked(tmp_path, monkeypatch):
    pv = pytest.importorskip("pyvista")
    pv.PolyData(np.random.default_rng(0).random((50, 3))).save(str(tmp_path / "p.vtp"))
    with pytest.raises(SystemExit) as exc:
        _run(
            monkeypatch,
            "pardesline.ops.pyvista_analysis.scalar_stats",
            ["--input", tmp_path / "p.vtp", "--output", tmp_path / "o.vtp"],
        )
    assert exc.value.code == 1
    _run(
        monkeypatch,
        "pardesline.ops.pyvista_analysis.scalar_stats",
        ["--input", tmp_path / "p.vtp", "--output", tmp_path / "e.vtp", "--scalars", "elevation"],
    )


@pytest.mark.local
def test_p3_b13_open_input_is_flagged(tmp_path):
    o3d = pytest.importorskip("open3d")
    m = o3d.geometry.TriangleMesh.create_sphere(10.0, 20)
    tris = np.asarray(m.triangles)[5:]
    m.triangles = o3d.utility.Vector3iVector(tris)  # a hole
    o3d.io.write_triangle_mesh(str(tmp_path / "open.ply"), m)
    proc = _cli(
        "pardesline.ops.sdf.compute_sdf",
        ["--input", tmp_path / "open.ply", "--output", tmp_path / "o.ply", "--voxel_size", 1.0],
    )
    assert "not watertight" in proc.stderr
