"""Regression tests for the mesh and surface bugs of the 2026-11-15 audit.

"P3-An" = Part 3, entry An of the audit report. Every test builds its own synthetic data
with a known answer; nothing is downloaded.
"""

from __future__ import annotations

import importlib
import math
import re
import subprocess
import sys

import numpy as np
import pytest

o3d = pytest.importorskip("open3d")
pv = pytest.importorskip("pyvista")
pytestmark = pytest.mark.local


def run_script(monkeypatch, module: str, args: list) -> None:
    mod = importlib.import_module(module)
    monkeypatch.setattr(sys, "argv", [module, *map(str, args)])
    mod.main()


def run_cli(module: str, args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", module, *map(str, args)], capture_output=True, text=True, timeout=600
    )


def signed_volume(mesh) -> float:
    """Positive when the faces are oriented outward."""
    v, f = np.asarray(mesh.vertices), np.asarray(mesh.triangles)
    return float(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6.0)


@pytest.fixture(scope="module")
def sphere_mesh(tmp_path_factory):
    path = tmp_path_factory.mktemp("sphere") / "sphere.ply"
    m = o3d.geometry.TriangleMesh.create_sphere(radius=10.0, resolution=80)
    o3d.io.write_triangle_mesh(str(path), m)
    return path


@pytest.fixture(scope="module")
def cube_mesh(tmp_path_factory):
    path = tmp_path_factory.mktemp("cube") / "cube.ply"
    m = o3d.geometry.TriangleMesh.create_box(20.0, 20.0, 20.0).translate((-10.0, -10.0, -10.0))
    o3d.io.write_triangle_mesh(str(path), m)
    return path


@pytest.fixture(scope="module")
def sphere_cloud(tmp_path_factory):
    """8000 Poisson-disk points on a sphere of radius 10 (spacing ~0.34), no normals."""
    path = tmp_path_factory.mktemp("cloud") / "cloud.ply"
    o3d.utility.random.seed(0)
    pc = o3d.geometry.TriangleMesh.create_sphere(radius=10.0, resolution=80).sample_points_poisson_disk(8000)
    o3d.io.write_point_cloud(str(path), o3d.geometry.PointCloud(pc.points))
    return path


@pytest.fixture(scope="module")
def sdf_sphere(sphere_mesh, tmp_path_factory):
    out = tmp_path_factory.mktemp("sdf") / "sdf.ply"
    mp = pytest.MonkeyPatch()
    try:
        run_script(
            mp,
            "pardesline.ops.sdf.compute_sdf",
            ["--input", sphere_mesh, "--output", out, "--voxel_size", 0.5],
        )
    finally:
        mp.undo()
    return o3d.io.read_triangle_mesh(str(out))


def test_p3_a01_compute_sdf_output_faces_outward(sdf_sphere):
    """Reversing the marching-cubes vertex axes is a reflection: the volume was -4179.9."""
    assert signed_volume(sdf_sphere) == pytest.approx(4 / 3 * math.pi * 1000, rel=0.01)


def test_p3_a02_compute_sdf_output_has_no_degenerate_or_duplicate_faces(sdf_sphere):
    """allow_degenerate=True gave 48 degenerate and 18 duplicate faces on this sphere."""
    v = np.asarray(sdf_sphere.vertices)
    f = np.asarray(sdf_sphere.triangles)
    area = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    assert (area < 1e-12).sum() == 0
    assert len(np.unique(np.sort(f, axis=1), axis=0)) == len(f)


@pytest.mark.parametrize(
    "module", ["pardesline.ops.sdf.occupancy_reconstruction", "pardesline.ops.voxel_to_mesh.binary_erosion"]
)
def test_p3_a01_other_marching_cubes_outputs_face_outward(module, sphere_mesh, tmp_path, monkeypatch):
    out = tmp_path / "o.ply"
    run_script(monkeypatch, module, ["--input", sphere_mesh, "--output", out, "--voxel_size", 0.5])
    assert signed_volume(o3d.io.read_triangle_mesh(str(out))) > 0


@pytest.mark.parametrize("module", ["mesh_to_pcd_uniform", "mesh_to_pcd_poisson_disk"])
def test_p3_a03_sampling_seed_is_honoured(module, sphere_mesh, tmp_path, monkeypatch):
    """Open3D 0.19's samplers take no 'seed': the call always fell back to an unseeded run."""
    pts = []
    for k in range(2):
        out = tmp_path / f"o{k}.ply"
        run_script(
            monkeypatch,
            f"pardesline.ops.mesh_processing.{module}",
            ["--input", sphere_mesh, "--output", out, "--num_points", 1000, "--seed", 3],
        )
        pts.append(np.asarray(o3d.io.read_point_cloud(str(out)).points))
    assert np.array_equal(pts[0], pts[1])


@pytest.mark.slow
def test_p3_a04_poisson_normals_follow_the_point_spacing(sphere_cloud, tmp_path, monkeypatch):
    """A fixed normal radius of 0.1 (spacing 0.34): 86 % wrong normals, volume -28.9, not watertight."""
    out = tmp_path / "o.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.point_cloud_reconstruction.poisson",
        ["--input", sphere_cloud, "--output", out, "--depth", 8, "--density_quantile", 0],
    )
    m = o3d.io.read_triangle_mesh(str(out))
    assert signed_volume(m) == pytest.approx(4 / 3 * math.pi * 1000, rel=0.02)
    assert np.abs(np.linalg.norm(np.asarray(m.vertices), axis=1) - 10.0).max() < 0.5


def test_p3_a04_ball_pivoting_is_consistently_oriented(sphere_cloud, tmp_path, monkeypatch):
    """Ball pivoting with the 0.1 radius: watertight but signed volume +2.9 (mixed winding)."""
    out = tmp_path / "o.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.point_cloud_reconstruction.ball_pivoting",
        ["--input", sphere_cloud, "--output", out],
    )
    assert signed_volume(o3d.io.read_triangle_mesh(str(out))) == pytest.approx(
        4 / 3 * math.pi * 1000, rel=0.02
    )


@pytest.mark.parametrize(
    "module",
    [
        "mesh_processing.mesh_to_pcd_uniform",
        "mesh_processing.mesh_to_pcd_poisson_disk",
        "sdf.compute_sdf",
        "sdf.occupancy_reconstruction",
        "sdf.sdf_voxel_visualization",
        "voxel_to_mesh.binary_erosion",
        "collision_detection.penetration_depth",
        "collision_detection.sdf_collision",
    ],
)
def test_p3_a05_a_point_cloud_is_not_replaced_by_its_convex_hull(module, tmp_path, monkeypatch):
    """A half-sphere cloud became a closed dome with an invented flat base, exit 0."""
    d = np.random.default_rng(0).normal(size=(3000, 3))
    d = d[d[:, 2] > 0]
    path = tmp_path / "half.ply"
    o3d.io.write_point_cloud(
        str(path),
        o3d.geometry.PointCloud(
            o3d.utility.Vector3dVector(d / np.linalg.norm(d, axis=1, keepdims=True) * 10)
        ),
    )
    with pytest.raises(SystemExit) as exc:
        run_script(monkeypatch, f"pardesline.ops.{module}", ["--input", path, "--output", tmp_path / "o.ply"])
    assert exc.value.code == 1


def _max_depth(proc) -> float:
    m = re.search(r"Max penetration depth: ([0-9.]+)", proc.stderr)
    assert m, proc.stderr[-1500:]
    return float(m.group(1))


@pytest.mark.slow
def test_p3_a06_a07_penetration_depth_on_a_cube(cube_mesh, tmp_path):
    """Cube of edge 20, obstacle radius 5, requested overlap 2: the obstacle was placed from the
    corner distance (17.3) and missed ("no penetration"); with the placement fixed, one ray per
    point gave a depth of 6.83 (a point outside counted inside). Expected 2.0."""
    proc = run_cli(
        "pardesline.ops.collision_detection.penetration_depth",
        [
            "--input",
            cube_mesh,
            "--output",
            tmp_path / "o.ply",
            "--obstacle_radius",
            5,
            "--overlap_distance",
            2,
            "--num_samples",
            200000,
        ],
    )
    assert proc.returncode == 0
    assert _max_depth(proc) == pytest.approx(2.0, abs=0.05)


def test_p3_a07_sign_from_three_rays():
    """A point 6.83 outside a sphere of radius 5 received -6.83 from Open3D's single ray."""
    from pardesline.ops._mesh_common import occupancy, signed_distance

    obs = o3d.geometry.TriangleMesh.create_sphere(radius=5.0, resolution=50).translate((13.0, 0.0, 0.0))
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(obs))
    probe = o3d.core.Tensor(np.array([[10.0, -8.96542728, -7.10836379]], np.float32))
    exact = float(np.linalg.norm([10.0 - 13.0, -8.96542728, -7.10836379]) - 5.0)
    assert scene.compute_signed_distance(probe).numpy()[0] < 0  # the single-ray defect, still in Open3D
    assert signed_distance(scene, probe)[0] == pytest.approx(exact, abs=0.05)
    assert occupancy(scene, probe)[0] == 0.0


def test_p3_a08_penetrating_points_are_red(sphere_mesh, tmp_path, monkeypatch):
    """Penetrating points (negative SDF) were coloured at the blue end of coolwarm."""
    out = tmp_path / "o.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.collision_detection.sdf_collision",
        [
            "--input",
            sphere_mesh,
            "--output",
            out,
            "--obstacle_radius",
            5,
            "--penetration_ratio",
            0.4,
            "--num_samples",
            20000,
        ],
    )
    pc = o3d.io.read_point_cloud(str(out))
    pts, col = np.asarray(pc.points)[:20000], np.asarray(pc.colors)[:20000]
    inside = np.linalg.norm(pts - [10.0 + 5.0 - 2.0, 0, 0], axis=1) < 5.0 - 0.05
    assert inside.sum() > 10
    assert (col[inside, 0] > col[inside, 2]).all()
    far = np.linalg.norm(pts - [13.0, 0, 0], axis=1) > 5.0 + 3.0
    assert (col[far, 2] > col[far, 0]).all()


def _oblique_ball(path, deg=25.0):
    t = math.radians(deg)
    d = np.array([[math.cos(t), -math.sin(t), 0], [math.sin(t), math.cos(t), 0], [0, 0, 1]])
    g = pv.ImageData(dimensions=(70, 56, 40), spacing=(0.6, 0.9, 1.5), origin=(5.0, -3.0, 2.0))
    g.direction_matrix = d
    c = np.asarray(g.points).mean(0)
    g.point_data["mask"] = (np.linalg.norm(np.asarray(g.points) - c, axis=1) < 12).astype(np.float32)
    g.save(str(path))
    return c


def test_p3_a09_contour_respects_the_direction_matrix(tmp_path, monkeypatch):
    """vtkContourFilter ignores the direction: centroid error (12.40, -6.43, 0) mm by default."""
    c = _oblique_ball(tmp_path / "ball.vti")
    out = tmp_path / "s.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.pyvista_volume_processing.contour",
        ["--input", tmp_path / "ball.vti", "--output", out, "--scalars", "mask", "--n_contours", 1],
    )
    assert np.allclose(np.asarray(pv.read(str(out)).points).mean(0), c, atol=0.05)
    with pytest.raises(SystemExit):
        run_script(
            monkeypatch,
            "pardesline.ops.pyvista_volume_processing.contour",
            [
                "--input",
                tmp_path / "ball.vti",
                "--output",
                tmp_path / "x.ply",
                "--scalars",
                "mask",
                "--n_contours",
                1,
                "--method",
                "contour",
            ],
        )


@pytest.fixture
def box_volume(tmp_path):
    g = pv.ImageData(dimensions=(41, 11, 11), spacing=(1.0, 1.0, 1.0), origin=(-10.0, 0.0, 0.0))
    g.point_data["v"] = np.asarray(g.points)[:, 0].astype(np.float32)
    path = tmp_path / "vol.vti"
    g.save(str(path))
    return path


def test_p3_a10_slice_at_zero_is_at_zero(box_volume, tmp_path, monkeypatch):
    """The volume spans x = -10..30; a slice asked at x = 0 was cut at the centre, x = 10."""
    out = tmp_path / "s.vtp"
    run_script(
        monkeypatch,
        "pardesline.ops.pyvista_volume_processing.slice",
        [
            "--input",
            box_volume,
            "--output",
            out,
            "--normal_x",
            1,
            "--normal_y",
            0,
            "--normal_z",
            0,
            "--origin_x",
            0,
            "--origin_y",
            0,
            "--origin_z",
            0,
        ],
    )
    assert np.allclose(pv.read(str(out)).points[:, 0], 0.0, atol=1e-6)
    out = tmp_path / "o.vtp"
    run_script(
        monkeypatch,
        "pardesline.ops.pyvista_volume_processing.slice_orthogonal",
        ["--input", box_volume, "--output", out, "--x", 0],
    )
    xs = pv.read(str(out)).points[:, 0]
    assert np.isclose(xs, 0.0).any() and not np.isclose(xs, 10.0).all()


def test_p3_a11_empty_results_are_errors(tmp_path, monkeypatch):
    tet = pv.UnstructuredGrid(
        {pv.CellType.TETRA: np.array([[0, 1, 2, 3]])},
        np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float),
    )
    tet.save(str(tmp_path / "tet.vtu"))
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.pyvista_volume_processing.extract_cells",
            ["--input", tmp_path / "tet.vtu", "--output", tmp_path / "o.vtu", "--cell_type", "hexahedral"],
        )
    assert exc.value.code == 1
    g = pv.ImageData(dimensions=(10, 10, 10))
    g.point_data["mask"] = (np.arange(1000) % 2).astype(np.float32)
    g.save(str(tmp_path / "mask.vti"))
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.pyvista_volume_processing.threshold_volume",
            ["--input", tmp_path / "mask.vti", "--output", tmp_path / "t.vtu", "--lower", 5, "--upper", 6],
        )
    assert exc.value.code == 1


def test_p3_a12_distance_is_described_as_what_it_computes():
    from pardesline.catalog import load_catalog

    meth = load_catalog().method("pyvista_analysis", "pv_distance")
    text = load_catalog().module("pyvista_analysis").theory["methods"]["pv_distance"]["content"]
    assert "Bounding-Box Centre" in meth.name and "unsigned" in text and "reference surface" not in text
    doc = importlib.import_module("pardesline.ops.pyvista_analysis.distance").__doc__
    assert "signed distance from center" not in doc and "bounding box" in doc


def test_p3_a13_scalar_stats_refuses_a_vector_array(sphere_mesh, tmp_path, monkeypatch):
    """The only array was Normals (3 components): statistics of flattened components, exit 0."""
    m = pv.Sphere(radius=10).compute_normals(cell_normals=False)
    for k in list(m.point_data.keys()):
        if k != "Normals":
            del m.point_data[k]
    m.save(str(tmp_path / "n.vtp"))
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.pyvista_analysis.scalar_stats",
            ["--input", tmp_path / "n.vtp", "--output", tmp_path / "o.vtp"],
        )
    assert exc.value.code == 1


def test_p3_a14_a_tetrahedron_is_a_mesh():
    from pardesline.medical.pyvista_adapter import detect_geometry_type

    assert detect_geometry_type(pv.PlatonicSolid("tetrahedron")) == "mesh"  # 4 points, 4 faces
    assert detect_geometry_type(pv.PolyData(np.random.default_rng(0).random((10, 3)))) == "pointcloud"
    assert detect_geometry_type(pv.Line()) == "lines"


def test_p3_a15_pcd_reader_follows_the_header(tmp_path):
    from pardesline.medical.pyvista_adapter import _load_pcd

    head = (
        "VERSION .7\nFIELDS rgb x y z\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\n"
        "WIDTH 1\nHEIGHT 1\nPOINTS 1\n"
    )
    (tmp_path / "a.pcd").write_text(head + "DATA ascii\n0.5 1 2 3\n")
    assert np.allclose(_load_pcd(str(tmp_path / "a.pcd")).points, [[1, 2, 3]])  # was (0.5, 1, 2)
    (tmp_path / "b.pcd").write_bytes(
        (head.replace("rgb x y z", "x y z rgb") + "DATA binary\n").encode() + b"\0" * 16
    )
    with pytest.raises(ValueError, match="ASCII"):
        _load_pcd(str(tmp_path / "b.pcd"))
