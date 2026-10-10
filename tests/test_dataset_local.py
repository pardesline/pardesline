"""pl.scan + pl.load on a private folder: the four asking modes, roles, split."""

from __future__ import annotations

import json

import pytest

import pardesline as pl
from pardesline.data import DRAFT_NAME


def _make_study(root):
    """Two patients, each with a volume, a mask and a mesh; one stray text file."""
    for pid in ("p01", "p02"):
        d = root / pid
        (d / "ct").mkdir(parents=True)
        (d / "ct" / "scan.vti").write_bytes(b"\0")
        (d / "masks").mkdir()
        (d / "masks" / "liver.vti").write_bytes(b"\0")
        (d / "surface.stl").write_bytes(b"\0")
    (root / "README.txt").write_text("notes")
    return root


def test_scan_groups_by_folder_and_asks(tmp_path):
    m = pl.scan(_make_study(tmp_path / "study"))
    assert m.pairing == "folder" and [s.id for s in m.samples] == ["p01", "p02"]
    assert set(m.roles) == {"ct", "mask", "surface"}
    assert m.roles["mask"].type == "labels"  # folder "masks/" is a name hint
    assert m.roles["surface"].type == "mesh"
    fields = [q.field for q in m.questions]
    assert "license" in fields
    assert "roles.ct.units" in fields and "roles.surface.units" in fields  # vti/stl carry no unit
    assert "roles.surface.frame" in fields
    assert "roles.mask.labels" in fields
    assert m.is_draft


def test_strict_load_raises_and_saves_draft(tmp_path):
    root = _make_study(tmp_path / "study")
    with pytest.raises(pl.NeedsConfirmation) as exc:
        pl.load(root)
    err = exc.value
    assert err.questions and err.draft_path == root / DRAFT_NAME and err.draft_path.is_file()
    text = str(err)
    assert "license=" in text and "units={" in text and "labels={" in text
    draft = json.loads(err.draft_path.read_text())
    assert draft["name"] == "study" and draft["questions"]


def test_answers_in_the_call(tmp_path):
    root = _make_study(tmp_path / "study")
    ds = pl.load(
        root,
        license="internal, no redistribution",
        units="mm",
        frame={"surface": "LPS"},
        labels={"mask": {1: "liver"}},
        pairing="folder",
    )
    assert isinstance(ds, pl.Dataset) and not ds.is_draft and len(ds) == 2
    assert ds.license.note == "internal, no redistribution"
    s = ds["p01"]
    assert s.roles == ["ct", "mask", "surface"]
    mask = s.mask
    assert isinstance(mask, pl.LabelMap) and mask.labels == {1: "liver"} and mask.units == "mm"
    assert mask.frame.source == "manifest" and mask.role == "mask"
    assert s.surface.frame.describe() == "LPS, mm (manifest)"
    assert mask.license is ds.license
    assert mask.provenance[0]["step"] == "load" and mask.provenance[0]["sample"] == "p01"
    assert s["ct"] is s.ct  # cached
    with pytest.raises(AttributeError):
        _ = s.mri
    assert ds.filter(**{}).ids == ["p01", "p02"]
    assert [o.role for o in ds.role("surface")] == ["surface", "surface"]
    assert len(list(ds.volumes)) == 4 and len(list(ds.meshes)) == 2


def test_spdx_string_is_a_licence_id(tmp_path):
    root = _make_study(tmp_path / "study")
    ds = pl.load(root, license="CC-BY-4.0", assume=True)
    assert ds.license.spdx == "CC-BY-4.0"


def test_assume_loads_with_warnings(tmp_path):
    root = _make_study(tmp_path / "study")
    ds = pl.load(root, assume=True)
    assert ds.is_draft and len(ds) == 2
    assert ds[0].ct.units is None  # unknown stays unknown


def test_saved_draft_is_reused_after_editing(tmp_path):
    root = _make_study(tmp_path / "study")
    with pytest.raises(pl.NeedsConfirmation):
        pl.load(root)
    draft = json.loads((root / DRAFT_NAME).read_text())
    draft["license"] = {"spdx": "CC0-1.0"}
    draft["roles"]["ct"]["units"] = "mm"
    draft["roles"]["surface"].update({"units": "mm", "frame": "LPS"})
    draft["roles"]["mask"].update({"units": "mm", "labels": {"1": "liver"}})
    draft["questions"] = []
    (root / DRAFT_NAME).write_text(json.dumps(draft))
    ds = pl.load(root)
    assert ds.license.spdx == "CC0-1.0" and ds[1].ct.units == "mm"


def test_interactive_mode(tmp_path, monkeypatch):
    root = _make_study(tmp_path / "study")
    by_field = {
        "license": "internal",
        "roles.ct.units": "mm",
        "roles.mask.units": "mm",
        "roles.mask.labels": "1: liver, 2: tumor",
        "roles.surface.units": "mm",
        "roles.surface.frame": "Z-up",
    }

    def fake_input(prompt=""):
        field = prompt.strip().split(":")[0]
        return by_field[field]

    monkeypatch.setattr("builtins.input", fake_input)
    ds = pl.load(root, interactive=True)
    assert not ds.is_draft
    assert ds[0].mask.labels == {1: "liver", 2: "tumor"}


def test_flat_folder_with_name_prefix(tmp_path):
    root = tmp_path / "flat"
    root.mkdir()
    for pid in ("a", "b", "c"):
        (root / f"{pid}_image.vti").write_bytes(b"\0")
        (root / f"{pid}_seg.vti").write_bytes(b"\0")
    m = pl.scan(root)
    assert m.pairing == "name_prefix" and [s.id for s in m.samples] == ["a", "b", "c"]
    assert set(m.roles) == {"image", "seg"} and m.roles["seg"].type == "labels"


def test_single_files_are_their_own_samples(tmp_path):
    root = tmp_path / "clouds"
    root.mkdir()
    (root / "scan1.ply").write_bytes(b"\0")
    (root / "scan2.ply").write_bytes(b"\0")
    m = pl.scan(root)
    assert m.pairing == "file" and len(m.samples) == 2 and list(m.roles) == ["points"]


def test_empty_folder(tmp_path):
    (tmp_path / "x").mkdir()
    with pytest.raises(FileNotFoundError, match="no 3D data"):
        pl.scan(tmp_path / "x")


def test_split_keeps_groups_together(tmp_path):
    root = tmp_path / "study"
    for pid in range(10):
        for ph in ("00", "50"):
            d = root / f"p{pid:02d}" / ph
            d.mkdir(parents=True)
            (d / "ct.vti").write_bytes(b"\0")
    ds = pl.load(root, assume=True)
    assert len(ds) == 10
    train, test = ds.split(fractions=(0.7, 0.3), seed=1)
    assert len(train) + len(test) == 10 and not set(train.ids) & set(test.ids)
    a, b, c = ds.split(fractions=(0.5, 0.25, 0.25))
    assert len(a) + len(b) + len(c) == 10
    with pytest.raises(ValueError):
        ds.split(fractions=(0.5, 0.6))
    assert len(ds.take(3)) == 3 and len(ds.sample(4, seed=0)) == 4


def test_manifest_file_can_be_loaded_directly(tmp_path):
    root = _make_study(tmp_path / "study")
    ds = pl.load(root, license="internal", assume=True)
    path = ds.manifest.save(tmp_path / "study.manifest.json")
    ds2 = pl.load(path)
    assert ds2.name == "study" and len(ds2) == 2
