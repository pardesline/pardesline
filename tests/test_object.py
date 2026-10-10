"""pl.Object: kinds, frames, labels, licence, provenance, sidecars."""

from __future__ import annotations

import json
import os

import pytest

import pardesline as pl
from pardesline.object import ALIASES, SIDECAR_SUFFIX, extension_of, kind_of


@pytest.mark.parametrize(
    "name,kind,cls",
    [
        ("a.ply", "pointcloud", pl.PointCloud),
        ("a.PCD", "pointcloud", pl.PointCloud),
        ("a.stl", "mesh", pl.Mesh),
        ("a.obj", "mesh", pl.Mesh),
        ("a.glb", "mesh", pl.Mesh),
        ("a.vti", "volume", pl.Volume),
        ("a.mha", "volume", pl.Volume),
        ("a.nii.gz", "volume", pl.Volume),
        ("a.tfm", "transform", pl.Transform),
        ("a.png", "image", pl.Image),
        ("a.docx", "file", pl.Object),
    ],
)
def test_kind_and_class_by_extension(tmp_path, name, kind, cls):
    assert kind_of(name) == kind
    f = tmp_path / name
    f.write_bytes(b"\0")
    assert type(pl.load(f)) is cls


def test_extension_of_handles_nii_gz():
    assert extension_of("x.nii.gz") == ".nii.gz"
    assert extension_of("x.NII") == ".nii"


def test_object_basics(tmp_path):
    f = tmp_path / "bunny.ply"
    f.write_bytes(b"ply\n" * 10)
    o = pl.load(f)
    assert o.kind == "pointcloud" and o.name == "bunny.ply" and o.extension == ".ply"
    assert os.fspath(o) == str(f)
    assert "bunny.ply" in repr(o) and "unknown axes" in repr(o)
    assert o.frame.axes is None and o.units is None and not o.frame.known
    assert not o.license.known and o.license.describe() == "unknown licence"
    assert o.transform is None and o.labels is None
    assert "point_cloud_processing.voxel_downsample" in o.methods()
    assert "simpleitk_segmentation.otsu_threshold" not in o.methods()
    assert "voxel_size" in o.describe_method("downsample")
    assert "frame:" in o.describe()
    with pytest.raises(FileNotFoundError):
        pl.load(tmp_path / "nope.ply")


def test_format_frame_for_gltf(tmp_path):
    f = tmp_path / "model.glb"
    f.write_bytes(b"glTF")
    o = pl.load(f)
    assert (o.axes, o.units, o.frame.source) == ("Y-up", "m", "format")


def test_with_frame_labels_license(tmp_path):
    f = tmp_path / "scan.ply"
    f.write_bytes(b"ply")
    o = pl.load(f).with_frame("Z-up", "mm").with_license("CC-BY-4.0")
    assert o.frame.known and o.frame.source == "user" and o.frame.describe() == "Z-up, mm (user)"
    assert o.license.spdx == "CC-BY-4.0" and o.license.known
    v = tmp_path / "seg.vti"
    v.write_bytes(b"\0")
    lm = pl.load(v).with_labels({1: "liver", 2: "tumor"})
    assert isinstance(lm, pl.LabelMap) and lm.kind == "labels" and lm.labels == {1: "liver", 2: "tumor"}
    assert lm.label_id("tumor") == 2
    with pytest.raises(KeyError):
        lm.label_id("spleen")


def test_save_writes_sidecar_and_reloads(tmp_path):
    f = tmp_path / "scan.ply"
    f.write_bytes(b"ply")
    o = pl.load(f).with_frame("Z-up", "m").with_license({"spdx": "MIT", "commercial": True})
    dest = o.save(tmp_path / "out" / "copy.ply")
    side = dest.with_name(dest.name + SIDECAR_SUFFIX)
    assert side.is_file()
    data = json.loads(side.read_text())
    assert (
        data["kind"] == "pointcloud" and data["frame"]["axes"] == "Z-up" and data["license"]["spdx"] == "MIT"
    )
    back = pl.load(dest)
    assert back.frame.axes == "Z-up" and back.units == "m" and back.license.commercial is True
    into_dir = o.save(str(tmp_path / "dir") + "/")
    assert into_dir.name == "scan.ply" and into_dir.parent.name == "dir"
    again = o.save(tmp_path / "dir")
    assert again == into_dir


def test_sidecar_labels_make_a_labelmap(tmp_path):
    v = tmp_path / "seg.mha"
    v.write_bytes(b"\0")
    (tmp_path / ("seg.mha" + SIDECAR_SUFFIX)).write_text(
        json.dumps({"kind": "labels", "labels": {"3": "left_atrium"}})
    )
    o = pl.load(v)
    assert isinstance(o, pl.LabelMap) and o.labels == {3: "left_atrium"}


def test_registration_sidecar_and_transform(tmp_path):
    f = tmp_path / "reg.vti"
    f.write_bytes(b"\0")
    f.with_suffix(".json").write_text(json.dumps({"transform": {"rotation_deg": [1, 2, 3]}, "stats": {}}))
    o = pl.load(f)
    assert o.transform == {"rotation_deg": [1, 2, 3]}
    dest = o.save(tmp_path / "out" / "copy.vti")
    assert dest.with_suffix(".json").is_file()


def test_aliases_resolve_in_the_catalog():
    cat = pl.catalog()
    for alias, (module, method) in ALIASES.items():
        assert cat.method(module, method), alias
        assert hasattr(pl.Object, alias), alias


def test_labelmap_to_mesh_needs_a_label(tmp_path):
    v = tmp_path / "seg.mha"
    v.write_bytes(b"\0")
    lm = pl.load(v).with_labels({1: "a", 2: "b"})
    with pytest.raises(pl.ParameterError, match="which label"):
        lm.to_mesh()


def test_missing_dependency_message(tmp_path, monkeypatch):
    f = tmp_path / "a.ply"
    f.write_bytes(b"ply")
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "open3d":
            raise ImportError
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(pl.MissingDependency, match=r"pip install 'pardesline\[local\]'"):
        pl.load(f).to_open3d()
