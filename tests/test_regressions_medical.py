"""Regression tests for the medical-volume bugs of the 2026-11-15 audit.

Each test names the entry it covers ("P1-n" = Part 1, entry n of the audit report;
"X-n" = docs/audit/2026-11-additional-findings.md). Every test builds its own synthetic
data with a known answer; nothing is downloaded.
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np
import pytest
from _synthetic import ball_mask, blob_volume, image_from_array, moved_copy, rotation_z, tre

sitk = pytest.importorskip("SimpleITK")
pytestmark = pytest.mark.medical


@pytest.fixture(scope="module")
def svc():
    from pardesline.medical import _service

    return _service


def _run_script(monkeypatch, module: str, args: list[str]) -> None:
    import importlib

    mod = importlib.import_module(module)
    monkeypatch.setattr(sys, "argv", [module, *args])
    mod.main()


def _bspline_of(transform):
    """The BSplineTransform inside a (possibly nested) composite."""
    if transform.GetName() == "BSplineTransform":
        return sitk.BSplineTransform(transform)
    if transform.GetName() == "CompositeTransform":
        comp = sitk.CompositeTransform(transform)
        for i in range(comp.GetNumberOfTransforms()):
            found = _bspline_of(comp.GetNthTransform(i))
            if found is not None:
                return found
    return None


# ----------------------------------------------------------------------------- registration
def test_p1_02_advanced_rigid_composes_search_then_refinement(svc, monkeypatch):
    """With SetMovingInitialTransform(M), the optimised O is applied first: the full map is
    p -> M(O(p)), i.e. CompositeTransform([M, O]). The stages are pinned to known transforms
    so that the test checks the composition, not the optimiser."""
    fixed, pts = blob_volume(size=(24, 24, 24), spacing=(2.0, 2.0, 2.0))
    m = sitk.Euler3DTransform((0, 0, 0), 0.0, 0.0, math.radians(90), (5.0, -3.0, 4.0))
    o = sitk.Euler3DTransform((10.0, 5.0, 0.0), math.radians(3), 0.0, math.radians(8), (2.0, 1.0, -1.0))

    class PinnedRefinement(sitk.ImageRegistrationMethod):
        def Execute(self, fixed_image, moving_image):
            return sitk.CompositeTransform([o])  # what Execute(inPlace=False) returns

        def GetMetricValue(self):
            return 0.0

        def GetOptimizerStopConditionDescription(self):
            return "pinned"

    monkeypatch.setattr(svc, "_find_best_rotation", lambda *a, **k: m)
    monkeypatch.setattr(svc.sitk, "ImageRegistrationMethod", PinnedRefinement)
    _, result = svc.register_rigid_advanced(fixed, fixed, num_iterations=1)
    expected = np.array([m.TransformPoint(o.TransformPoint(tuple(p))) for p in pts])
    got = np.array([result.TransformPoint(tuple(p)) for p in pts])
    assert np.abs(got - expected).max() < 1e-9  # the old order O(M(p)) is off by ~10 mm here


@pytest.mark.slow
def test_p1_03_rotation_search_samples_every_voxel_and_is_reproducible(svc):
    """5 % random sampling at shrink 8 picked a wrong pose in 3 runs out of 4."""
    fixed, pts = blob_volume(size=(80, 80, 64), spacing=(1.5, 1.5, 1.5))
    s_map = sitk.Euler3DTransform((0, 0, 0), 0.0, 0.0, math.radians(90), (5.0, -3.0, 4.0))
    moving = moved_copy(fixed, s_map)
    truth = s_map.GetInverse()
    params = []
    for _ in range(3):
        found = svc._find_best_rotation(fixed, moving, steps_per_axis=4)
        assert tre(found, truth, pts) < 1.0
        params.append(np.array(found.GetParameters()))
    # rotations identical; translations from the moments initializer agree to float32 sums
    assert all(np.allclose(p, params[0], atol=1e-3) for p in params)


@pytest.fixture(scope="module")
def bspline_pair():
    fixed, _ = blob_volume(size=(48, 48, 48), spacing=(2.0, 2.0, 2.0))  # 96 mm per side
    rng = np.random.default_rng(0)
    deform = sitk.BSplineTransformInitializer(fixed, [3, 3, 3], 3)
    deform.SetParameters(tuple(rng.normal(0.0, 2.0, len(deform.GetParameters()))))
    return fixed, moved_copy(fixed, deform)


@pytest.mark.slow
def test_p1_04_bspline_grid_is_the_requested_one(svc, bspline_pair):
    """grid_spacing 24 mm on a 96 mm volume is a 4 x 4 x 4 mesh (was 1 x 1 x 1: never refined)."""
    fixed, moving = bspline_pair
    registered, tx = svc.register_bspline(fixed, moving, grid_spacing=24.0, num_iterations=50)
    bs = _bspline_of(tx)
    assert bs is not None
    assert list(bs.GetTransformDomainMeshSize()) == [4, 4, 4]
    f = sitk.GetArrayFromImage(fixed)
    before = np.abs(f - sitk.GetArrayFromImage(moving))[8:-8, 8:-8, 8:-8].mean()
    after = np.abs(f - sitk.GetArrayFromImage(registered))[8:-8, 8:-8, 8:-8].mean()
    assert after < 0.5 * before


@pytest.mark.slow
def test_p1_05_registration_results_write_to_h5(svc, bspline_pair, tmp_path, monkeypatch):
    """Nested composites cannot be written by ITK's HDF5 writer; results are flattened."""
    fixed, moving = bspline_pair
    _, bs_tx = svc.register_bspline(fixed, moving, grid_spacing=48.0, num_iterations=10)
    small, _ = blob_volume(size=(32, 32, 32), spacing=(2.0, 2.0, 2.0))
    monkeypatch.setattr(
        svc,
        "_find_best_rotation",
        lambda *a, **k: sitk.CompositeTransform(
            [sitk.Euler3DTransform((0, 0, 0), 0.0, 0.0, 0.2, (1.0, 0.0, 0.0))]
        ),
    )
    _, adv_tx = svc.register_rigid_advanced(small, small, num_iterations=5)
    probe = [(3.0, -4.0, 5.0), (-10.0, 7.5, 2.0)]
    for name, tx in (("bspline", bs_tx), ("advanced", adv_tx)):
        path = tmp_path / f"{name}.h5"
        svc.save_transform(tx, path)
        back = sitk.ReadTransform(str(path))
        for p in probe:
            assert np.allclose(back.TransformPoint(p), tx.TransformPoint(p), atol=1e-6)


def test_p1_10_displacement_summary_is_a_length(svc):
    """A uniform field (3, -3, 0) mm has magnitude 4.243 mm everywhere; the mean was 0."""
    field = np.zeros((6, 7, 8, 3), np.float64)
    field[..., 0], field[..., 1] = 3.0, -3.0
    img = sitk.GetImageFromArray(field, isVector=True)
    d = svc.transform_to_dict(sitk.DisplacementFieldTransform(img))
    assert d["mean_displacement_mm"] == pytest.approx(math.hypot(3, 3), abs=1e-4)
    assert d["max_displacement_mm"] == pytest.approx(math.hypot(3, 3), abs=1e-4)
    assert d["std_displacement_mm"] == pytest.approx(0.0, abs=1e-4)


@pytest.mark.slow
def test_p1_19_registration_is_reproducible_by_default(svc):
    """Random metric sampling used the wall clock: two identical runs gave different transforms."""
    fixed, _ = blob_volume(size=(40, 40, 32), spacing=(1.5, 1.5, 2.0))
    moving = moved_copy(fixed, sitk.Euler3DTransform((0, 0, 0), 0.05, -0.03, 0.08, (3.0, -2.0, 1.0)))
    # Same seed, same samples: only multithreaded floating-point sums differ (~1e-15).
    # Unseeded runs differed by up to 0.09 rad on this pair.
    a = svc.register_rigid(fixed, moving, num_iterations=30)[1].GetParameters()
    b = svc.register_rigid(fixed, moving, num_iterations=30)[1].GetParameters()
    assert np.allclose(a, b, rtol=0, atol=1e-9)
    c = svc.register_affine(fixed, moving, num_iterations=20)[1].GetParameters()
    d = svc.register_affine(fixed, moving, num_iterations=20)[1].GetParameters()
    assert np.allclose(c, d, rtol=0, atol=1e-9)


REG_SCRIPTS = [
    "rigid_registration",
    "affine_registration",
    "advanced_rigid_registration",
    "bspline_registration",
    "demons_registration",
    "difference_analysis",
]


@pytest.mark.parametrize("script", REG_SCRIPTS)
def test_p1_20_registration_scripts_require_moving(script, tmp_path, monkeypatch):
    """Without --moving the scripts registered the fixed image with a moved copy of itself."""
    fixed, _ = blob_volume(size=(16, 16, 16), spacing=(2.0, 2.0, 2.0))
    path = tmp_path / "fixed.mha"
    sitk.WriteImage(fixed, str(path))
    with pytest.raises(SystemExit) as exc:
        _run_script(
            monkeypatch,
            f"pardesline.ops.simpleitk_registration.{script}",
            ["--input", str(path), "--output", str(tmp_path / "out.vti")],
        )
    assert exc.value.code == 2
    assert not (tmp_path / "out.vti").exists()


@pytest.mark.local
@pytest.mark.slow
def test_p1_19_seed_is_a_script_parameter_and_is_reported(tmp_path, monkeypatch):
    fixed, _ = blob_volume(size=(24, 24, 24), spacing=(2.0, 2.0, 2.0))
    moving = moved_copy(fixed, sitk.TranslationTransform(3, (2.0, -1.0, 1.0)))
    sitk.WriteImage(fixed, str(tmp_path / "f.mha"))
    sitk.WriteImage(moving, str(tmp_path / "m.mha"))
    out = tmp_path / "reg.vti"
    _run_script(
        monkeypatch,
        "pardesline.ops.simpleitk_registration.rigid_registration",
        [
            "--input",
            str(tmp_path / "f.mha"),
            "--moving",
            str(tmp_path / "m.mha"),
            "--output",
            str(out),
            "--num_iterations",
            "10",
            "--seed",
            "7",
        ],
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert sidecar["seed"] == 7


# ----------------------------------------------------------------------------- segmentation
def _ct_phantom():
    """Air -1000 HU, soft-tissue cube 40 HU, bone core 1200 HU (32^3, 1 mm)."""
    a = np.full((32, 32, 32), -1000.0, np.float32)
    a[6:26, 6:26, 6:26] = 40.0
    a[12:20, 12:20, 12:20] = 1200.0
    return image_from_array(a)


def test_p1_06_otsu_keeps_voxels_brighter_than_255(svc):
    mask = sitk.GetArrayFromImage(svc.threshold_otsu(_ct_phantom()))
    assert mask[16, 16, 16] == 1  # bone (was 0: BinaryThreshold's default upper bound is 255)
    assert mask[8, 8, 8] == 1 and mask[0, 0, 0] == 0


@pytest.mark.local
def test_p1_07_connected_components_default_upper_bound_is_the_image_maximum(tmp_path, monkeypatch, svc):
    a = np.zeros((32, 32, 32), np.float32)
    a[4:10, 4:10, 4:10] = 1200.0  # bone-like object
    a[20:28, 20:28, 20:28] = 300.0
    sitk.WriteImage(image_from_array(a), str(tmp_path / "ct.mha"))
    out = tmp_path / "cc.vti"
    _run_script(
        monkeypatch,
        "pardesline.ops.simpleitk_segmentation.connected_components",
        ["--input", str(tmp_path / "ct.mha"), "--output", str(out), "--threshold", "100"],
    )
    labels = sitk.GetArrayFromImage(svc.load_volume(out))
    assert len(np.unique(labels[labels > 0])) == 2
    assert labels[6, 6, 6] > 0 and labels[24, 24, 24] > 0


def test_p1_08_watershed_seed_radius_is_in_mm(svc):
    """Sphere of radius 20 mm on 2 mm voxels: the centre is 20 mm (10 voxels) deep.
    A 12 mm seed radius must give a seed; in voxels it asked for 24 mm and found none."""
    sp = (2.0, 2.0, 2.0)
    m = ball_mask((40, 40, 40), sp, [(40.0, 40.0, 40.0)], 20.0)
    labels = svc.segment_watershed(
        image_from_array(m, spacing=sp),
        seed_radius=12.0,
        min_object_size=1,
        opening_radius="1,1,1",
        closing_radius="1,1,1",
    )
    a = sitk.GetArrayFromImage(labels)
    assert len(np.unique(a[a > 0])) == 1
    assert (a > 0).sum() > 0.9 * m.sum()


def _two_touching_spheres():
    sp = (1.0, 1.0, 1.0)
    # radius 10, centres 16 mm apart: the neck between them is a ring of radius 6 mm, so any
    # seed radius above 6 mm gives one seed per ball
    centres = [(20.0, 24.0, 24.0), (36.0, 24.0, 24.0)]
    cut = [(2.0, 24.0, 24.0)]  # a third ball cut by the image border
    m = ball_mask((48, 48, 56), sp, centres, 10.0) | ball_mask((48, 48, 56), sp, cut, 6.0)
    return m, sp


def test_p1_09_watershed_splits_touching_objects_and_drops_border_objects(svc):
    m, sp = _two_touching_spheres()
    labels = svc.segment_watershed(
        image_from_array(m, spacing=sp),
        seed_radius=7.0,
        min_object_size=1,
        opening_radius="1,1,1",
        closing_radius="1,1,1",
    )
    a = sitk.GetArrayFromImage(labels)
    ids = [v for v in np.unique(a) if v != 0]
    assert len(ids) == 2  # was 0: boundary removal deleted every object
    vols = sorted(int((a == v).sum()) for v in ids)
    ball = 4.0 / 3.0 * math.pi * 10.0**3
    assert all(0.75 * ball < v < 1.05 * ball for v in vols)
    assert a[24, 24, 2] == 0  # the ball cut by the border is removed
    assert a[24, 24, 20] != 0 and a[24, 24, 36] != 0 and a[24, 24, 20] != a[24, 24, 36]


@pytest.mark.local
def test_p1_09_watershed_script_output_is_not_empty(tmp_path, monkeypatch, svc):
    m, sp = _two_touching_spheres()
    sitk.WriteImage(image_from_array(m.astype(np.float32) * 1200.0, spacing=sp), str(tmp_path / "v.mha"))
    out = tmp_path / "ws.vti"
    _run_script(
        monkeypatch,
        "pardesline.ops.simpleitk_segmentation.watershed",
        [
            "--input",
            str(tmp_path / "v.mha"),
            "--output",
            str(out),
            "--threshold",
            "100",
            "--seed_radius",
            "7",
            "--min_object_size",
            "1",
            "--opening_radius",
            "1,1,1",
            "--closing_radius",
            "1,1,1",
        ],
    )
    a = sitk.GetArrayFromImage(svc.load_volume(out))
    assert len(np.unique(a[a > 0])) == 2


# ----------------------------------------------------------------------------- volume I/O
@pytest.mark.local
def test_p1_15_volume_to_vti_keeps_the_direction(svc, tmp_path):
    pv = pytest.importorskip("pyvista")
    d = rotation_z(30.0)
    img = image_from_array(
        np.arange(12 * 16 * 20, dtype=np.float32).reshape(12, 16, 20),
        spacing=(0.8, 1.1, 2.0),
        origin=(5.0, -3.0, 7.0),
        direction=d,
    )
    path = tmp_path / "oblique.vti"
    svc.volume_to_vti(img, path)
    grid = pv.read(str(path))
    assert np.allclose(np.asarray(grid.direction_matrix), d)
    ijk = (15, 3, 7)
    flat = ijk[0] + 20 * (ijk[1] + 16 * ijk[2])
    assert np.allclose(grid.points[flat], img.TransformIndexToPhysicalPoint(ijk), atol=1e-6)
    assert grid.point_data["intensity"][flat] == sitk.GetArrayFromImage(img)[7, 3, 15]


@pytest.mark.local
def test_p1_16_load_volume_reads_the_direction_of_a_vti(svc, tmp_path):
    pv = pytest.importorskip("pyvista")
    d = rotation_z(25.0)
    arr = np.arange(5 * 6 * 7, dtype=np.float32).reshape(7, 6, 5)  # (z, y, x)
    grid = pv.ImageData(dimensions=(5, 6, 7), spacing=(0.5, 0.7, 1.3), origin=(1.0, 2.0, 3.0))
    grid.direction_matrix = d
    grid.point_data["intensity"] = arr.reshape(-1)
    grid.save(str(tmp_path / "v.vti"))
    img = svc.load_volume(tmp_path / "v.vti")
    assert np.allclose(np.array(img.GetDirection()).reshape(3, 3), d)
    assert np.array_equal(sitk.GetArrayFromImage(img), arr)
    assert np.allclose(img.TransformIndexToPhysicalPoint((4, 2, 3)), grid.points[4 + 5 * (2 + 6 * 3)])


@pytest.mark.local
def test_p1_17_load_volume_reads_the_file_it_was_given(svc, tmp_path):
    pv = pytest.importorskip("pyvista")
    grid = pv.ImageData(dimensions=(4, 4, 4))
    grid.point_data["intensity"] = np.full(64, 1.0, np.float32)
    grid.save(str(tmp_path / "v.vti"))
    sitk.WriteImage(image_from_array(np.full((4, 4, 4), 2.0, np.float32)), str(tmp_path / "v.mha"))
    assert float(sitk.GetArrayFromImage(svc.load_volume(tmp_path / "v.vti")).max()) == 1.0


def test_p1_18_dicom_slices_are_stacked_by_position(svc, tmp_path):
    """Each slice written with its own series UID: GDCM finds no multi-slice series and the
    fallback stacked files in name order ([20, 30, 50, 0, 40, 10], z spacing 0.5 mm)."""
    names = ["f3", "f5", "f0", "f1", "f4", "f2"]
    for k in range(6):
        img = sitk.GetImageFromArray(np.full((1, 8, 8), 10 * k, np.int16))
        img.SetSpacing((0.7, 0.7, 2.5))
        img.SetOrigin((0.0, 0.0, 2.5 * k))
        img.SetMetaData("0008|0060", "CT")
        img.SetMetaData("0020|0032", f"0\\0\\{2.5 * k}")
        img.SetMetaData("0020|0037", "1\\0\\0\\0\\1\\0")
        sitk.WriteImage(img, str(tmp_path / f"slice_{names[k]}.dcm"))
    vol = svc.load_dicom(tmp_path)
    assert sitk.GetArrayFromImage(vol)[:, 0, 0].tolist() == [0, 10, 20, 30, 40, 50]
    assert vol.GetSpacing()[2] == pytest.approx(2.5)
    assert vol.GetOrigin()[2] == pytest.approx(0.0)


# ----------------------------------------------------------------------------- additional findings
# X-n: docs/audit/2026-11-additional-findings.md


def test_x01_difference_analysis_counts_every_large_difference(svc):
    """Voxels whose difference exceeded the 400 upper bound were not counted as 'high difference':
    the worse the misalignment, the better the reported score."""
    a = np.zeros((10, 10, 10), np.float32)
    b = a.copy()
    b[0:2] = 100.0  # 200 voxels off by 100
    b[5:7] = 1000.0  # 200 voxels off by 1000
    _, stats = svc.compute_difference_thresholded(image_from_array(a), image_from_array(b))
    assert stats["high_diff_voxels"] == 400  # was 200


def test_x02_watershed_does_not_give_a_seedless_object_its_neighbours_label(svc):
    """A separate object too thin for a seed was reached through the background by a
    neighbour's basin and carried its label (the report's corrected snippet does this)."""
    sp = (1.0, 1.0, 1.0)
    big = ball_mask((40, 40, 48), sp, [(16.0, 20.0, 20.0)], 10.0)
    small = ball_mask((40, 40, 48), sp, [(36.0, 20.0, 20.0)], 4.0)  # 4 mm deep: no 7 mm seed
    labels = sitk.GetArrayFromImage(
        svc.segment_watershed(
            image_from_array(big | small, spacing=sp),
            seed_radius=7.0,
            min_object_size=1,
            opening_radius="1,1,1",
            closing_radius="1,1,1",
        )
    )
    assert labels[20, 20, 16] != 0
    assert labels[20, 20, 36] == 0


def test_x03_initializer_name_is_not_silently_replaced(svc):
    """'geometry' (lower case) silently ran the MOMENTS initializer."""
    fixed, _ = blob_volume(size=(24, 24, 20), spacing=(2.0, 2.0, 2.0))
    moving = moved_copy(fixed, sitk.TranslationTransform(3, (3.0, 0.0, 0.0)))
    upper = svc.get_initial_transform(fixed, moving, "GEOMETRY").GetParameters()
    lower = svc.get_initial_transform(fixed, moving, "geometry").GetParameters()
    assert np.allclose(upper, lower)
    with pytest.raises(ValueError, match="initializer"):
        svc.get_initial_transform(fixed, moving, "CENTER")


def test_x04_unknown_metric_name_is_an_error(svc):
    """A misspelt metric ('mean_square') silently ran Mattes mutual information."""
    with pytest.raises(ValueError, match="metric"):
        svc._configure_registration(sitk.ImageRegistrationMethod(), metric="mean_square")
