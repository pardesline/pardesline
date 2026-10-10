from __future__ import annotations

import json
import os

import pytest

import pardesline as pl
from pardesline.object import ALIASES, kind_of


@pytest.mark.parametrize(
    "name,kind",
    [
        ("a.ply", "pointcloud"),
        ("a.PCD", "pointcloud"),
        ("a.stl", "mesh"),
        ("a.obj", "mesh"),
        ("a.vti", "volume"),
        ("a.mha", "volume"),
        ("a.nii.gz", "volume"),
        ("a.tfm", "transform"),
        ("a.png", "image"),
        ("a.zip", "archive"),
        ("a.docx", "file"),
    ],
)
def test_kind_by_extension(name, kind):
    assert kind_of(name) == kind


def test_object_basics(tmp_path):
    f = tmp_path / "bunny.ply"
    f.write_bytes(b"ply\n" * 10)
    o = pl.load(f)
    assert o.kind == "pointcloud" and o.name == "bunny.ply" and o.extension == ".ply"
    assert os.fspath(o) == str(f)
    assert "pointcloud" in repr(o) and "bunny.ply" in repr(o)
    assert o.sidecar is None and o.transform is None
    assert "point_cloud_processing.voxel_downsample" in o.methods()
    assert "simpleitk_segmentation.otsu_threshold" not in o.methods()
    assert "voxel_size" in o.describe("downsample")
    with pytest.raises(FileNotFoundError):
        pl.load(tmp_path / "nope.ply")


def test_sidecar_and_transform(tmp_path):
    f = tmp_path / "reg.vti"
    f.write_bytes(b"\0")
    f.with_suffix(".json").write_text(json.dumps({"transform": {"rotation_deg": [1, 2, 3]}, "stats": {}}))
    o = pl.load(f)
    assert o.transform == {"rotation_deg": [1, 2, 3]}


def test_save_copies_file_and_sidecar(tmp_path):
    f = tmp_path / "reg.vti"
    f.write_bytes(b"\0\1")
    f.with_suffix(".json").write_text("{}")
    o = pl.load(f)
    dest = o.save(tmp_path / "out" / "copy.vti")
    assert dest.read_bytes() == b"\0\1" and dest.with_suffix(".json").is_file()
    into_dir = o.save(str(tmp_path / "dir") + "/")  # trailing slash = "put it in this folder"
    assert into_dir.name == "reg.vti" and into_dir.parent.name == "dir"
    again = o.save(tmp_path / "dir")  # an existing folder works too
    assert again == into_dir


def test_aliases_resolve_in_the_catalog():
    cat = pl.catalog()
    for alias, (module, method) in ALIASES.items():
        assert cat.method(module, method), alias
        assert hasattr(pl.Object, alias), alias


def test_load_rejects_uris_and_folders_clearly(tmp_path):
    with pytest.raises(NotImplementedError, match="hf://"):
        pl.load("hf://org/name")
    with pytest.raises(NotImplementedError, match="folder"):
        pl.load(tmp_path)


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
