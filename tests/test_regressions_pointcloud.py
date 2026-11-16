"""Regression tests for the point-cloud bugs of the 2026-11-15 audit.

"P2-An" = Part 2, entry An of the audit report; "X-n" = docs/audit/2026-11-additional-findings.md.
Every test builds its own synthetic data with a known answer (mm units); nothing is downloaded.
"""

from __future__ import annotations

import importlib
import json
import sys

import numpy as np
import pytest
from _synthetic import pose_error, registration_pair, rot_xyz, write_ply

o3d = pytest.importorskip("open3d")
pytestmark = pytest.mark.local


def run_script(monkeypatch, module: str, args: list[str]) -> None:
    mod = importlib.import_module(module)
    monkeypatch.setattr(sys, "argv", [module, *map(str, args)])
    mod.main()


def run_cli(module: str, args: list) -> int:
    """Run a script in a fresh interpreter, as the runner does (thread settings apply)."""
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-m", module, *map(str, args)], capture_output=True, text=True, timeout=600
    )
    return proc.returncode


def sidecar(out) -> dict:
    return json.loads(out.with_suffix(".json").read_text())


@pytest.fixture(scope="module")
def near_symmetric_pair(tmp_path_factory):
    """Box-like part whose small features make single RANSAC runs flip (3 of 6 runs 91 deg off).
    The moving cloud carries per-point colours and normals that the output must keep."""
    d = tmp_path_factory.mktemp("pair")
    f, m, t = registration_pair(n=4000, feature=0.3, overlap=0.8)
    rng = np.random.default_rng(3)
    colors = rng.random((len(m), 3))
    normals = rng.normal(size=(len(m), 3))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    write_ply(d / "f.ply", f)
    write_ply(d / "m.ply", m, colors=colors, normals=normals)
    return d, t, colors, normals


SCRIPTS = ["ransac_global", "icp_refinement", "ransac_icp_pipeline"]


@pytest.mark.parametrize("script", SCRIPTS)
def test_p2_a01_registration_requires_moving(script, near_symmetric_pair, tmp_path, monkeypatch):
    """Without --moving the scripts registered the fixed cloud with a moved copy of itself."""
    d, *_ = near_symmetric_pair
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            f"pardesline.ops.registration.{script}",
            ["--input", d / "f.ply", "--output", tmp_path / "o.ply"],
        )
    assert exc.value.code == 2
    assert not (tmp_path / "o.ply").exists()


@pytest.mark.parametrize("script", ["ransac_global", "icp_refinement"])
def test_p2_a02_voxel_size_is_used_as_given(script, near_symmetric_pair, tmp_path, monkeypatch):
    """5.0 lies outside 0.5-5 % of the 74 mm diagonal: it was replaced by 1.3 % without a trace."""
    d, *_ = near_symmetric_pair
    out = tmp_path / "o.ply"
    # these tests check attributes / the recorded voxel, not quality: a single RANSAC run on this
    # near-symmetric part can land below the 0.5.0 quality floor (fitness 0.31-0.44 on Linux CI)
    extra = [*(["--restarts", 1] if script == "ransac_global" else []), "--min_fitness", 0]
    run_script(
        monkeypatch,
        f"pardesline.ops.registration.{script}",
        ["--input", d / "f.ply", "--moving", d / "m.ply", "--output", out, "--voxel_size", 5.0, *extra],
    )
    assert sidecar(out)["voxel_size"] == 5.0


@pytest.fixture(scope="module")
def pipeline_run(near_symmetric_pair, tmp_path_factory):
    d, t, colors, normals = near_symmetric_pair
    out = tmp_path_factory.mktemp("pipe") / "aligned.ply"
    mp = pytest.MonkeyPatch()
    try:
        run_script(
            mp,
            "pardesline.ops.registration.ransac_icp_pipeline",
            ["--input", d / "f.ply", "--moving", d / "m.ply", "--output", out],
        )
    finally:
        mp.undo()
    return out, t, colors, normals


@pytest.mark.slow
def test_p2_a03_pipeline_finds_the_pose_of_a_near_symmetric_part(pipeline_run):
    """One unseeded RANSAC run flipped this part by 91 degrees in 3 of 6 runs."""
    out, t, *_ = pipeline_run
    sc = sidecar(out)
    rot, trans = pose_error(sc["transformation_matrix"], t)
    assert rot < 1.0 and trans < 0.5
    assert sc["status"] == "ok" and sc["seed"] == 0 and sc["restarts"] == 8
    assert len(sc["candidates"]) >= 8


@pytest.mark.slow
@pytest.mark.xfail(
    sys.platform == "darwin",
    reason="macOS: Open3D's RANSAC is not repeatable under a seed even with OMP_NUM_THREADS=1 "
    "(observed on macOS CI, 2026-11-15; documented limitation)",
    strict=False,
)
def test_p2_a03_x07_same_seed_same_result(near_symmetric_pair, tmp_path):
    """Unseeded runs differed (A3); seeded runs still differed (5.06 vs 7.15 degrees) because
    Open3D's parallel RANSAC threads share one generator (X7)."""
    d, *_ = near_symmetric_pair
    mats = []
    for k in range(3):
        out = tmp_path / f"g{k}.ply"
        rc = run_cli(
            "pardesline.ops.registration.ransac_global",
            ["--input", d / "f.ply", "--moving", d / "m.ply", "--output", out, "--restarts", 2, "--seed", 5],
        )
        assert rc == 0
        mats.append(np.array(sidecar(out)["transformation_matrix"]))
    assert all(np.allclose(m, mats[0], atol=1e-9) for m in mats)


@pytest.mark.slow
def test_p2_a03_ransac_global_keeps_the_best_of_several_seeds(near_symmetric_pair, tmp_path, monkeypatch):
    d, t, *_ = near_symmetric_pair
    out = tmp_path / "g.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.registration.ransac_global",
        ["--input", d / "f.ply", "--moving", d / "m.ply", "--output", out],
    )
    sc = sidecar(out)
    # coarse, but not a flip (90-180 deg): RANSAC-only poses were 5 deg off on Windows, 15.6 on macOS CI
    assert pose_error(sc["transformation_matrix"], t)[0] < 30.0
    assert sc["first_seed"] == 0 and len(sc["candidates"]) == 8


def test_p2_a04_icp_in_two_passes_converges_from_ransac_sized_errors(near_symmetric_pair):
    """From starts off by 5 degrees and N(0, 2v) per axis (the size of RANSAC errors), one
    pass at 0.4v stalled above 0.1 mm in 18 of 20 starts on this part; 1.5v then 0.4v in 1
    of 20 (the remaining slide is what the pipeline's restarts and scoring are for)."""
    from pardesline.ops.registration import _common as c

    d, t, *_ = near_symmetric_pair
    fixed = o3d.io.read_point_cloud(str(d / "f.ply"))
    moving = o3d.io.read_point_cloud(str(d / "m.ply"))
    v = 0.013 * c.bbox_diag(fixed)
    nrm = o3d.geometry.KDTreeSearchParamHybrid(radius=2 * v, max_nn=30)
    fixed.estimate_normals(nrm)
    moving.estimate_normals(nrm)
    crit = o3d.pipelines.registration.ICPConvergenceCriteria(1e-6, 1e-6, 100)
    rng = np.random.default_rng(0)
    failed = {"one": 0, "two": 0}
    for _ in range(20):
        axis = rng.normal(size=3)
        p = np.eye(4)
        p[:3, :3] = o3d.geometry.get_rotation_matrix_from_axis_angle(
            axis / np.linalg.norm(axis) * np.radians(5)
        )
        p[:3, 3] = rng.normal(0, 2 * v, 3)
        for key, passes in (("one", [0.4 * v]), ("two", [1.5 * v, 0.4 * v])):
            result, stages = c.icp_passes(moving, fixed, p @ t, passes, "point_to_plane", crit)
            assert result is not None and len(stages) == len(passes)
            failed[key] += pose_error(result.transformation, t)[1] > 0.1
    assert failed["one"] >= 10 and failed["two"] <= 2


def test_p2_a19_point_to_point_fallback_uses_the_criteria(near_symmetric_pair):
    """The fallback ran with Open3D's default 30 iterations whatever was asked."""
    from pardesline.ops.registration import _common as c

    d, t, *_ = near_symmetric_pair
    fixed = o3d.io.read_point_cloud(str(d / "f.ply"))  # no normals: point-to-plane raises
    moving = o3d.io.read_point_cloud(str(d / "m.ply"))
    start = np.eye(4)
    start[:3, 3] = [2.0, -1.5, 1.0]
    start = start @ t
    res = {}
    for n in (1, 60):
        crit = o3d.pipelines.registration.ICPConvergenceCriteria(1e-9, 1e-9, n)
        result, stages = c.icp_passes(moving, fixed, start, [5.0], "point_to_plane", crit)
        assert stages[0]["estimation"] == "point_to_point"
        res[n] = pose_error(result.transformation, t)[1]
    assert res[60] < 0.5 * res[1]  # one iteration really is one iteration


def test_p2_a19_pipeline_keeps_and_labels_the_ransac_pose_when_icp_finds_nothing(
    near_symmetric_pair, tmp_path, monkeypatch
):
    d, *_ = near_symmetric_pair
    out = tmp_path / "o.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.registration.ransac_icp_pipeline",
        [
            "--input",
            d / "f.ply",
            "--moving",
            d / "m.ply",
            "--output",
            out,
            "--restarts",
            1,
            "--symmetry_probe",
            "false",
            "--icp_coarse_threshold_factor",
            0,
            "--icp_threshold_factor",
            1e-9,
            # this test checks the labelling of a RANSAC-only result, not its quality (0.5.0 floor)
            "--min_fitness",
            0,
        ],
    )
    sc = sidecar(out)
    assert sc["result_stage"].startswith("RANSAC only")
    assert sc["candidates"][0]["transformation_matrix"] == sc["transformation_matrix"]


@pytest.mark.slow
def test_p2_a14_output_keeps_the_moving_clouds_colours_and_normals(pipeline_run):
    """The output was painted yellow and its normals re-estimated."""
    out, _t, colors, normals = pipeline_run
    got = o3d.io.read_point_cloud(str(out))
    assert np.allclose(np.asarray(got.colors), colors, atol=1 / 255)
    tm = np.array(sidecar(out)["transformation_matrix"])
    assert np.allclose(np.asarray(got.normals), normals @ tm[:3, :3].T, atol=1e-5)


@pytest.mark.parametrize("script", ["ransac_global", "icp_refinement"])
def test_p2_a14_other_registration_outputs_keep_attributes(
    script, near_symmetric_pair, tmp_path, monkeypatch
):
    d, _t, colors, _ = near_symmetric_pair
    out = tmp_path / "o.ply"
    # these tests check attributes / the recorded voxel, not quality: a single RANSAC run on this
    # near-symmetric part can land below the 0.5.0 quality floor (fitness 0.31-0.44 on Linux CI)
    extra = [*(["--restarts", 1] if script == "ransac_global" else []), "--min_fitness", 0]
    run_script(
        monkeypatch,
        f"pardesline.ops.registration.{script}",
        ["--input", d / "f.ply", "--moving", d / "m.ply", "--output", out, *extra],
    )
    assert np.allclose(np.asarray(o3d.io.read_point_cloud(str(out)).colors), colors, atol=1 / 255)


_ = rot_xyz  # re-exported helper used by other tests of this module


# ----------------------------------------------------------------------------- deformable
def _bump_pair(n: int, seed: int = 0):
    """(fixed, moving, truth) in mm: moving_i = fixed[perm_i] pushed by a Gaussian bump (6 mm
    along x, sigma 15 mm) plus 0.1 mm noise; truth_i = fixed[perm_i] is where it belongs."""
    from _synthetic import asym_object_points

    rng = np.random.default_rng(seed)
    fixed = asym_object_points(n, seed=seed)
    c = np.array([fixed[:, 0].min(), fixed[:, 1].mean(), fixed[:, 2].mean()])
    bump = 6.0 * np.exp(-np.sum((fixed - c) ** 2, axis=1) / (2 * 15.0**2))
    perm = rng.permutation(n)
    moving = (fixed + np.c_[bump, 0 * bump, 0 * bump] + rng.normal(0, 0.1, fixed.shape))[perm]
    return fixed, moving, fixed[perm]


@pytest.fixture(scope="module")
def bump_files(tmp_path_factory):
    pytest.importorskip("pycpd")
    d = tmp_path_factory.mktemp("bump")
    fixed, moving, truth = _bump_pair(800)
    write_ply(d / "f.ply", fixed)
    write_ply(d / "m.ply", moving)
    return d, fixed, moving, truth


def _cpd(monkeypatch, d, out, *extra):
    run_script(
        monkeypatch,
        "pardesline.ops.deformable_registration.cpd_deformable",
        ["--input", d / "f.ply", "--moving", d / "m.ply", "--output", out, *extra],
    )
    pts = np.asarray(o3d.io.read_point_cloud(str(out)).points)
    return pts[-800:]  # the output is fixed (first) + registered moving (in moving order)


@pytest.mark.slow
def test_p2_a06_cpd_defaults_improve_the_correspondence(bump_files, tmp_path, monkeypatch):
    """Scale grew with sqrt(N) and beta defaulted to 100: the result was worse than the input
    (1.11 -> 1.34 mm mean). With the RMS scale and beta 2 it is ~0.2 mm."""
    d, _, moving, truth = bump_files
    before = np.linalg.norm(moving - truth, axis=1).mean()
    reg = _cpd(monkeypatch, d, tmp_path / "o.ply")
    after = np.linalg.norm(reg - truth, axis=1).mean()
    assert after < 0.4 * before


@pytest.mark.slow
def test_p2_a05_cpd_tolerance_reaches_pycpd(bump_files, tmp_path, monkeypatch):
    """pycpd 2 names it 'tolerance': 'tol' was swallowed, so every tolerance gave the same result."""
    d, *_ = bump_files
    loose = _cpd(monkeypatch, d, tmp_path / "a.ply", "--tolerance", 0.5)
    tight = _cpd(monkeypatch, d, tmp_path / "b.ply", "--tolerance", 1e-9, "--max_iterations", 150)
    assert np.abs(loose - tight).max() > 1e-3


def test_p2_a05_cpd_low_rank_is_refused(bump_files, tmp_path, monkeypatch):
    d, *_ = bump_files
    with pytest.raises(SystemExit) as exc:
        _cpd(monkeypatch, d, tmp_path / "o.ply", "--low_rank", "true")
    assert exc.value.code == 1


def test_x05_cpd_requires_moving(bump_files, tmp_path, monkeypatch):
    """Without --moving, CPD deformed a copy of the fixed cloud and registered it back."""
    d, *_ = bump_files
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.deformable_registration.cpd_deformable",
            ["--input", d / "f.ply", "--output", tmp_path / "o.ply"],
        )
    assert exc.value.code == 2


def _gauss(monkeypatch, path, out, *extra):
    run_script(
        monkeypatch,
        "pardesline.ops.deformable_registration.gaussian_deformation",
        ["--input", path, "--output", out, *extra],
    )
    return np.asarray(o3d.io.read_point_cloud(str(out)).points)


def test_p2_a07_gaussian_deformation_is_continuous_at_the_radius(tmp_path, monkeypatch):
    """Points just inside the radius moved by 13.5 % of the peak, points just outside by 0."""
    rng = np.random.default_rng(0)
    pts = rng.uniform(-50, 50, (40000, 3))
    pts[0] = [-50.0, 0.0, 0.0]  # the pressure centre is (min x, mean y, mean z)
    write_ply(tmp_path / "c.ply", pts)
    out = _gauss(monkeypatch, tmp_path / "c.ply", tmp_path / "o.ply", "--radius", 30, "--displacement", 5)
    src = np.asarray(o3d.io.read_point_cloud(str(tmp_path / "c.ply")).points)
    centre = np.array([src[:, 0].min(), src[:, 1].mean(), src[:, 2].mean()])
    dist = np.linalg.norm(src - centre, axis=1)
    moved = np.linalg.norm(out - src, axis=1)
    shell = (dist > 29.0) & (dist < 30.0)
    assert shell.any() and moved[shell].max() < 0.05 * 5  # was 0.68-0.77 mm (13.5 %)
    assert moved[dist >= 30.0].max() == 0.0
    assert moved.max() <= 5.0 + 1e-9


def test_p2_a08_gaussian_deformation_that_moves_nothing_is_an_error(tmp_path, monkeypatch):
    """Defaults (radius 0.1, displacement 0.02) reached no point of a cloud in mm: the input
    was written back with exit code 0."""
    pts = np.random.default_rng(0).uniform(0, 100, (2000, 3))
    write_ply(tmp_path / "c.ply", pts)
    with pytest.raises(SystemExit) as exc:  # radius and displacement are now required
        _gauss(monkeypatch, tmp_path / "c.ply", tmp_path / "o.ply")
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        _gauss(monkeypatch, tmp_path / "c.ply", tmp_path / "o2.ply", "--radius", 1e-3, "--displacement", 1)
    assert exc.value.code == 1
    assert not (tmp_path / "o2.ply").exists()


# ----------------------------------------------------------------------------- processing / segmentation
def _scene(seed: int = 0) -> np.ndarray:
    """SCENE of the audit, in mm: plane z = 0 of 200 x 200 (8000 points, noise 0.05),
    spheres r 15 and r 10 above it, 150 uniform outliers."""
    rng = np.random.default_rng(seed)
    plane = np.c_[rng.uniform(-100, 100, (8000, 2)), rng.normal(0, 0.05, 8000)]
    d = rng.normal(size=(3000, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    s1 = d[:1800] * 15 + [-30.0, 20.0, 40.0]
    s2 = d[1800:] * 10 + [40.0, -25.0, 60.0]
    out = rng.uniform([-100, -100, 0], [100, 100, 100], (150, 3))
    return np.vstack([plane, s1, s2, out])


@pytest.fixture(scope="module")
def scene_ply(tmp_path_factory):
    return write_ply(tmp_path_factory.mktemp("scene") / "scene.ply", _scene())


def test_p2_a09_clustering_with_nothing_left_is_an_error(scene_ply, tmp_path, monkeypatch):
    """ground_threshold 1000 removed everything: the input was written as the result, exit 0."""
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.lidar_scene_detection.object_clustering",
            ["--input", scene_ply, "--output", tmp_path / "o.ply", "--ground_threshold", 1000],
        )
    assert exc.value.code == 1
    assert not (tmp_path / "o.ply").exists()


def test_p2_a10_mesh_to_pointcloud_refuses_a_point_cloud(scene_ply, tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.point_cloud_processing.mesh_to_pointcloud",
            ["--input", scene_ply, "--output", tmp_path / "o.ply"],
        )
    assert exc.value.code == 1


def test_p2_a11_threshold_without_scalars_is_an_error(scene_ply, tmp_path, monkeypatch):
    """Without scalars it thresholded the distance to an arbitrary 1 x 1 plane (13 150 -> 2 points)."""
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.pyvista_pointcloud_processing.threshold",
            ["--input", scene_ply, "--output", tmp_path / "o.ply"],
        )
    assert exc.value.code == 1


def test_p2_a12_random_sample_is_seeded_and_keeps_duplicates(scene_ply, tmp_path, monkeypatch):
    pv = pytest.importorskip("pyvista")
    outs = []
    for k in range(2):
        out = tmp_path / f"r{k}.ply"
        run_script(
            monkeypatch,
            "pardesline.ops.pyvista_pointcloud_processing.random_sample",
            ["--input", scene_ply, "--output", out, "--fraction", 0.3],
        )
        outs.append(np.asarray(pv.read(str(out)).points))
    assert np.array_equal(outs[0], outs[1])  # was: same count, different points
    out = tmp_path / "rep.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.pyvista_pointcloud_processing.random_sample",
        ["--input", scene_ply, "--output", out, "--fraction", 0.5, "--replace", "true", "--seed", 0],
    )
    n = len(_scene())
    assert pv.read(str(out)).n_points == int(n * 0.5)  # logged 6575, wrote 5145


BOX_FAR = ["--x_min", 500, "--x_max", 600, "--y_min", 500, "--y_max", 600, "--z_min", 500, "--z_max", 600]


@pytest.mark.parametrize(
    "script,args",
    [
        ("clip_box", []),
        ("extract_points", []),
        ("clip_box", BOX_FAR),
        ("extract_points", ["--scalars", "elevation", "--lower", 500, "--upper", 600]),
        ("clip_plane", ["--origin_x", 1000, "--invert", "false"]),
    ],
)
def test_p2_a13_unit_scale_defaults_and_empty_results_are_errors(
    script, args, scene_ply, tmp_path, monkeypatch
):
    """Defaults of +-0.5 and [0, 1] kept nothing (or a 1 mm slab) of data in mm, written with exit 0."""
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            f"pardesline.ops.pyvista_pointcloud_processing.{script}",
            ["--input", scene_ply, "--output", tmp_path / "o.ply", *args],
        )
    assert exc.value.code == 1
    assert not (tmp_path / "o.ply").exists()


def test_p2_a17_clip_plane_default_keeps_the_side_opposite_to_the_normal(scene_ply, tmp_path, monkeypatch):
    pv = pytest.importorskip("pyvista")
    out = tmp_path / "o.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.pyvista_pointcloud_processing.clip_plane",
        ["--input", scene_ply, "--output", out, "--origin_x", 0, "--origin_y", 0, "--origin_z", 0],
    )
    assert pv.read(str(out)).points[:, 0].max() <= 1e-6
    from pardesline.catalog import load_catalog

    text = (
        load_catalog().module("pyvista_pointcloud_processing").theory["methods"]["pv_clip_plane"]["content"]
    )
    assert "negative side" not in text and "opposite to the normal" in text


def test_p2_a15_ransac_plane_keeps_point_order_and_reports_the_plane(scene_ply, tmp_path, monkeypatch):
    out = tmp_path / "o.ply"
    run_script(
        monkeypatch,
        "pardesline.ops.point_cloud_segmentation.ransac_plane",
        ["--input", scene_ply, "--output", out, "--distance_threshold", 0.2],
    )
    src = np.asarray(o3d.io.read_point_cloud(str(scene_ply)).points)
    got = np.asarray(o3d.io.read_point_cloud(str(out)).points)
    assert np.allclose(got, src)  # inliers were moved first
    sc = sidecar(out)
    assert abs(abs(sc["plane_abcd"][2]) - 1.0) < 1e-3 and sc["inliers"] >= 7950  # 8000 plane points
    with pytest.raises(SystemExit) as exc:  # the 0.01 default found 1 304 of 8 000 plane points
        run_script(
            monkeypatch,
            "pardesline.ops.point_cloud_segmentation.ransac_plane",
            ["--input", scene_ply, "--output", tmp_path / "x.ply"],
        )
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "module",
    ["point_cloud_segmentation.ransac_plane", "lidar_scene_detection.ground_removal"],
)
def test_x06_plane_ransac_is_seeded(module, scene_ply, tmp_path):
    """segment_plane draws from Open3D's global generator, which nothing seeded."""
    res = []
    for k in range(3):
        out = tmp_path / f"o{k}.ply"
        assert (
            run_cli(
                f"pardesline.ops.{module}",
                ["--input", scene_ply, "--output", out, "--distance_threshold", 0.2, "--num_iterations", 20],
            )
            == 0
        )
        pcd = o3d.io.read_point_cloud(str(out))
        res.append(np.asarray(pcd.colors if "ransac" in module else pcd.points))
    assert all(r.shape == res[0].shape and np.array_equal(r, res[0]) for r in res)


@pytest.mark.parametrize(
    "module,value",
    [("lidar_camera_fusion.intensity_colorization", 3), ("stereo_3d_reconstruction.depth_colorization", 7)],
)
def test_p2_a16_unknown_colormap_number_is_an_error(module, value, scene_ply, tmp_path, monkeypatch):
    """A colormap number outside the documented list silently fell back to viridis / turbo."""
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            f"pardesline.ops.{module}",
            ["--input", scene_ply, "--output", tmp_path / "o.ply", "--colormap", value],
        )
    assert exc.value.code == 2


def test_p2_a16_descriptions_say_what_the_scripts_compute():
    from pardesline.catalog import load_catalog

    cat = load_catalog()
    lc = cat.module("lidar_camera_fusion")
    assert "No intensity" in lc.theory["methods"]["intensity_colorization"]["content"]
    assert "jet" not in cat.method("lidar_camera_fusion", "intensity_colorization").parameters[0].description
    assert "MEDIAN" in lc.theory["methods"]["roi_extraction"]["content"]
    assert "side by side" in lc.theory["methods"]["multi_resolution"]["content"]
    st = cat.module("stereo_3d_reconstruction")
    assert "z coordinate" in st.theory["methods"]["depth_colorization"]["content"]
    assert "not depths" in st.theory["methods"]["depth_filter"]["content"]


def test_x08_height_colorization_unknown_colormap_is_an_error(scene_ply, tmp_path, monkeypatch):
    """Any number outside 0-3 silently used viridis."""
    with pytest.raises(SystemExit) as exc:
        run_script(
            monkeypatch,
            "pardesline.ops.lidar_scene_detection.height_colorization",
            ["--input", scene_ply, "--output", tmp_path / "o.ply", "--colormap", 9],
        )
    assert exc.value.code == 2
