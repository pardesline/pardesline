"""Regression tests for the core defects reported by a downstream project (2026-11 review).

"I-n" = item n of the review (object saving, registration quality, licences, label volumes,
runner, manifests); "X-n" = docs/audit/2026-11-additional-findings.md. Synthetic data, no network.
"""

from __future__ import annotations

import json
import math
import subprocess

import numpy as np
import pytest

import pardesline as pl


def _volume(tmp_path, name="v.mha", arr=None, pixel=None):
    sitk = pytest.importorskip("SimpleITK")
    if arr is None:
        z, y, x = np.mgrid[0:20, 0:24, 0:28]
        arr = (((x - 14) ** 2 + (y - 12) ** 2 + (z - 10) ** 2) < 49).astype(np.float32) * 500.0
    img = sitk.GetImageFromArray(arr)
    t = math.radians(20)
    img.SetDirection((math.cos(t), -math.sin(t), 0, math.sin(t), math.cos(t), 0, 0, 0, 1))
    img.SetSpacing((0.8, 1.2, 2.0))
    img.SetOrigin((5.0, -3.0, 7.0))
    path = tmp_path / name
    sitk.WriteImage(img, str(path))
    return path


def _cloud(tmp_path, name, seed, license=None):
    o3d = pytest.importorskip("open3d")
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(1500, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    pts = d * [30.0, 20.0, 10.0]
    path = tmp_path / name
    o3d.io.write_point_cloud(str(path), o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts)))
    if license is not None:
        (tmp_path / (name + ".pardesline.json")).write_text(json.dumps({"license": license}))
    return path


# ----------------------------------------------------------------------------- I-1 frame after run
@pytest.mark.medical
@pytest.mark.local
def test_i01_run_output_frame_is_derived_and_keeps_the_grid(tmp_path, out_dir):
    vol = pl.load(_volume(tmp_path))
    assert vol.frame.source == "file" and vol.frame.affine is not None
    mask = vol.segment(lower=100, upper=1000)  # grid-preserving: same size, spacing, origin, direction
    assert mask.frame.source != "file"
    assert mask.frame.affine is not None
    assert np.allclose(np.array(mask.frame.affine), np.array(vol.frame.affine), atol=1e-6)
    surface = mask.to_mesh(label=1)
    assert surface.frame.source != "file" and surface.frame.affine is None


# ----------------------------------------------------------------------------- I-4 licences
COMMERCIAL = {"spdx": "CC-BY-4.0", "commercial": True, "redistribution": "allowed"}
NON_COMMERCIAL = {"spdx": "CC-BY-NC-4.0", "commercial": False, "redistribution": "allowed"}


@pytest.mark.local
@pytest.mark.slow
def test_i04_two_inputs_most_restrictive_licence_wins(tmp_path, out_dir):
    fixed = pl.load(_cloud(tmp_path, "f.ply", 0, COMMERCIAL))
    moving = pl.load(_cloud(tmp_path, "m.ply", 1, NON_COMMERCIAL))
    assert fixed.license.commercial is True and moving.license.commercial is False
    out = fixed.icp(moving, voxel_size=2.0)
    assert out.license.commercial is False
    assert out.license.spdx == "CC-BY-NC-4.0"


@pytest.mark.local
@pytest.mark.slow
def test_i04_an_unknown_licence_stays_unknown(tmp_path, out_dir):
    fixed = pl.load(_cloud(tmp_path, "f.ply", 0, COMMERCIAL))
    moving = pl.load(_cloud(tmp_path, "m.ply", 1))  # no licence stated
    out = fixed.icp(moving, voxel_size=2.0)
    assert not out.license.known and out.license.commercial is None


def test_i04_licence_table_orders_and_never_upgrades():
    from pardesline.object.frame import License, combine_licenses

    by = License.from_dict(COMMERCIAL)
    nc = License.from_dict(NON_COMMERCIAL)
    sa = License.from_dict({"spdx": "CC-BY-SA-4.0", "commercial": True})
    assert combine_licenses([by, nc]).spdx == "CC-BY-NC-4.0"
    assert combine_licenses([sa, by]).spdx == "CC-BY-SA-4.0"
    assert not combine_licenses([by, License()]).known
    odd = License.from_dict({"spdx": "LicenseRef-something-new", "commercial": True})
    assert not combine_licenses([by, odd]).known  # not in the table -> unknown
    assert combine_licenses([by]).spdx == "CC-BY-4.0"


@pytest.mark.local
def test_i04_tool_server_run_returns_the_licence_and_writes_the_sidecar(tmp_path, out_dir):
    from pardesline.mcp_server import impl_run_method

    src = _cloud(tmp_path, "c.ply", 0, NON_COMMERCIAL)
    res = impl_run_method("point_cloud_processing.voxel_downsample", str(src), params={"voxel_size": 0.5})
    assert res["license"]["spdx"] == "CC-BY-NC-4.0" and res["license"]["commercial"] is False
    from pathlib import Path

    side = json.loads(Path(res["output"] + ".pardesline.json").read_text(encoding="utf-8"))
    assert side["license"]["spdx"] == "CC-BY-NC-4.0"


# ----------------------------------------------------------------------------- I-5, I-6 label volumes
@pytest.mark.medical
def test_i05_large_label_ids_survive_load_and_save(tmp_path):
    sitk = pytest.importorskip("SimpleITK")
    big = 2**24 + 3  # not representable in float32
    arr = np.zeros((6, 7, 8), np.int32)
    arr[2:4, 2:5, 3:6] = big
    arr[0, 0, 0] = 5
    path = tmp_path / "labels.nrrd"
    sitk.WriteImage(sitk.GetImageFromArray(arr), str(path))
    labels = pl.load(path).as_labels({5: "a", big: "b"})
    assert int(labels.to_numpy().max()) == big
    out = labels.save(tmp_path / "copy.nrrd")
    assert int(sitk.GetArrayFromImage(sitk.ReadImage(str(out))).max()) == big


@pytest.mark.medical
def test_i06_resampling_a_label_map_invents_no_label(tmp_path, out_dir):
    sitk = pytest.importorskip("SimpleITK")
    arr = np.zeros((20, 20, 20), np.uint16)
    arr[:, :, 10:] = 3
    arr[5:15, 5:15, 2:8] = 7
    path = tmp_path / "lab.nrrd"
    img = sitk.GetImageFromArray(arr)
    img.SetSpacing((1.0, 1.0, 1.0))
    sitk.WriteImage(img, str(path))
    lab = pl.load(path).as_labels({3: "a", 7: "b"})
    out = lab.resample(spacing=(0.7, 0.7, 1.3))
    got = set(np.unique(out.to_numpy()).tolist())
    assert got <= {0, 3, 7}
    assert out.provenance[-1]["interpolator"] == "nearest"


@pytest.mark.medical
def test_i06_service_resample_takes_an_interpolator():
    sitk = pytest.importorskip("SimpleITK")
    from pardesline.medical import resample

    img = sitk.GetImageFromArray(np.array([[[0, 5, 5, 0]]], np.uint8))
    out = resample(img, new_spacing=(0.5, 1.0, 1.0), interpolator="nearest")
    assert set(np.unique(sitk.GetArrayFromImage(out)).tolist()) <= {0, 5}


# ----------------------------------------------------------------------------- I-7 runner stdin
def test_i07_runner_children_do_not_inherit_stdin(monkeypatch):
    from pardesline import runner

    seen = {}

    class Stop(Exception):
        pass

    def fake_popen(cmd, **kwargs):
        seen.update(kwargs)
        raise Stop

    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)
    with pytest.raises(Stop):
        runner._stream(["python", "-m", "x"], 5, None, None, None)
    assert seen.get("stdin") is subprocess.DEVNULL


# ----------------------------------------------------------------------------- I-3 registration quality
QUALITY_KEYS = {"status", "stop_condition", "iterations", "final_metric", "floors"}


@pytest.mark.local
@pytest.mark.slow
@pytest.mark.parametrize(
    "method",
    ["registration.ransac_global", "registration.icp_refinement", "registration.ransac_icp_pipeline"],
)
def test_i03_point_cloud_registration_of_unrelated_shapes_fails_loudly(method, tmp_path, out_dir):
    """Unrelated shapes registered with exit code 0 and fitness at most 0.063 (0.3.1)."""
    from _synthetic import asym_object_points, write_ply

    rng = np.random.default_rng(5)
    sph = rng.normal(size=(3000, 3))
    sph = sph / np.linalg.norm(sph, axis=1, keepdims=True) * 25
    fixed = write_ply(tmp_path / "f.ply", asym_object_points(4000, seed=0))
    moving = write_ply(tmp_path / "m.ply", sph)
    with pytest.raises(pl.RunError, match="exit code 4"):
        pl.run(method, fixed, tmp_path / "out.ply", moving=moving)
    q = json.loads((tmp_path / "out.json").read_text())["quality"]
    assert q["status"] == "below_floor" and q["fitness"] < 0.5 and set(q) >= QUALITY_KEYS


@pytest.mark.local
@pytest.mark.slow
def test_i03_point_cloud_registration_reports_its_quality(tmp_path, out_dir):
    from _synthetic import registration_pair, write_ply

    f, m, _ = registration_pair(n=3000)
    fixed = pl.load(write_ply(tmp_path / "f.ply", f))
    out = fixed.icp(write_ply(tmp_path / "m.ply", m))
    q = out.quality
    assert (
        q is not None and set(q) >= QUALITY_KEYS and {"fitness", "inlier_rmse", "fitness_threshold"} <= set(q)
    )
    assert q["status"] == "ok" and q["fitness"] > 0.8 and q["floors"] == {"min_fitness": 0.5}


@pytest.mark.medical
@pytest.mark.local
@pytest.mark.slow
def test_i03_volume_registration_of_unrelated_images_fails_loudly(tmp_path, out_dir):
    sitk = pytest.importorskip("SimpleITK")
    from _synthetic import blob_volume

    fixed, _ = blob_volume(size=(40, 40, 32), spacing=(1.5, 1.5, 2.0))
    noise = sitk.GetImageFromArray(
        np.random.default_rng(1).normal(50, 30, sitk.GetArrayFromImage(fixed).shape).astype(np.float32)
    )
    noise.CopyInformation(fixed)
    sitk.WriteImage(fixed, str(tmp_path / "f.mha"))
    sitk.WriteImage(noise, str(tmp_path / "m.mha"))
    with pytest.raises(pl.RunError, match="exit code 4"):
        pl.run(
            "simpleitk_registration.rigid", tmp_path / "f.mha", tmp_path / "o.vti", moving=tmp_path / "m.mha"
        )
    q = json.loads((tmp_path / "o.json").read_text())["quality"]
    assert q["status"] == "below_floor" and q["similarity"] < 0.05


@pytest.mark.medical
@pytest.mark.local
@pytest.mark.slow
@pytest.mark.parametrize("method", ["rigid", "affine", "demons"])
def test_i03_volume_registration_reports_its_quality(method, tmp_path, out_dir):
    sitk = pytest.importorskip("SimpleITK")
    from _synthetic import blob_volume, moved_copy

    fixed, _ = blob_volume(size=(40, 40, 32), spacing=(1.5, 1.5, 2.0))
    moving = moved_copy(fixed, sitk.TranslationTransform(3, (2.0, -1.5, 1.0)))
    sitk.WriteImage(fixed, str(tmp_path / "f.mha"))
    sitk.WriteImage(moving, str(tmp_path / "m.mha"))
    out = pl.load(tmp_path / "f.mha").run(f"simpleitk_registration.{method}", moving=tmp_path / "m.mha")
    q = out.quality
    assert q is not None and set(q) >= QUALITY_KEYS and {"overlap", "similarity"} <= set(q)
    assert q["status"] == "ok" and q["overlap"] > 0.5 and q["similarity"] > 0.1
    assert q["floors"] == {"min_overlap": 0.25, "min_similarity": 0.05}


@pytest.mark.medical
def test_i03_service_quality_of_a_no_overlap_transform_is_zero():
    sitk = pytest.importorskip("SimpleITK")
    from _synthetic import blob_volume

    from pardesline.medical import _service as svc

    fixed, _ = blob_volume(size=(24, 24, 20), spacing=(2.0, 2.0, 2.0))
    q = svc.registration_quality(fixed, fixed, sitk.TranslationTransform(3, (500.0, 0.0, 0.0)))
    assert q["overlap"] == 0.0
    assert svc.check_registration_quality(dict(q))["status"] == "below_floor"


# ----------------------------------------------------------------------------- additional findings
@pytest.mark.local
def test_x11_non_commercial_survives_a_save(tmp_path):
    """License.to_dict() dropped every False value: a saved non-commercial object reloaded as
    'commercial use unknown'."""
    src = _cloud(tmp_path, "c.ply", 0, NON_COMMERCIAL)
    out = pl.load(src).save(tmp_path / "copy.ply")
    back = pl.load(out)
    assert back.license.commercial is False and back.license.spdx == "CC-BY-NC-4.0"
