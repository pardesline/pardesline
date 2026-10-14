"""Manifest schema and the bundled manifests (no network)."""

from __future__ import annotations

import pytest

import pardesline as pl
from pardesline.data.dataset import _pattern_regex, derive_samples
from pardesline.data.manifest import DEFAULT_MIRRORS, Manifest

BUNDLED = pl.datasets()


def test_bundled_manifests_exist_and_are_valid():
    names = [m.name for m in BUNDLED]
    assert {"rire_brain", "popi_lung_4dct", "liver_tumor_patient01", "open3d_bunny"} <= set(names)
    assert len(names) == len(set(names))
    for m in BUNDLED:
        assert m.license.source_url or m.license.spdx, f"{m.name}: licence needs at least a source URL"
        assert m.citation, f"{m.name}: citation missing"
        assert not m.is_draft
        assert "TO CONFIRM" in (m.license.note or "") or m.license.spdx, m.name  # honest about unknown terms
        if m.source.scheme in ("https", "open3d"):
            assert m.samples, f"{m.name}: small bundled datasets list their samples explicitly"
        else:
            # hub repos and remote archives derive samples from a scoped listing
            assert all(r.pattern for r in m.roles.values()), f"{m.name}: every role needs a pattern"
            assert m.license.spdx, f"{m.name}: public hub/archive manifests state the licence id"
            assert m.license.commercial is not None or "TO CONFIRM" in (m.license.note or ""), m.name
        if m.source.scheme == "hf":
            assert m.source.paths, f"{m.name}: hf manifests scope the listing with source.paths"
        if m.source.scheme == "archive":
            assert m.source.archive_format in ("zip", "tar") and m.source.prefix, m.name
        for r in m.roles.values():
            if r.pattern and r.needs_layout(r.pattern):
                raise AssertionError(f"{m.name}: raw-array role without layout")
        for s in m.samples or []:
            for role, rel in s.files.items():
                assert role in m.roles
                if m.source.scheme == "https":
                    assert rel in m.source.files, f"{m.name}/{s.id}: {rel} has no hash"


def test_https_files_have_hashes_and_mirrors():
    m = next(x for x in BUNDLED if x.name == "rire_brain")
    spec = m.source.files["training_001_ct.mha"]
    assert len(spec.sha512) == 128
    assert all("{sha512}" in u for u in DEFAULT_MIRRORS)


def test_describe_lists_roles_and_licence():
    text = pl.describe("popi_lung_4dct")
    assert "ct" in text and "mask" in text and "labels 1=body, 2=lungs" in text and "licence" in text


def test_schema_rejects_bad_manifests():
    base = {
        "name": "x",
        "source": {"scheme": "local", "root": "."},
        "roles": {"ct": {"type": "volume", "pattern": "{id}/ct.mha"}},
    }
    Manifest.from_dict(base)
    with pytest.raises(pl.ManifestError, match="undeclared role"):
        Manifest.from_dict({**base, "samples": [{"id": "a", "files": {"mri": "a.mha"}}]})
    with pytest.raises(pl.ManifestError, match="unique"):
        Manifest.from_dict(
            {**base, "samples": [{"id": "a", "files": {"ct": "a"}}, {"id": "a", "files": {"ct": "b"}}]}
        )
    with pytest.raises(pl.ManifestError, match="needs a pattern"):
        Manifest.from_dict({**base, "roles": {"ct": {"type": "volume"}}})
    with pytest.raises(pl.ManifestError, match="root is required"):
        Manifest.from_dict({**base, "source": {"scheme": "local"}})
    with pytest.raises(pl.ManifestError, match="sha512"):
        Manifest.from_dict({**base, "source": {"scheme": "https", "files": {"a.mha": {"sha512": "abc"}}}})
    with pytest.raises(pl.ManifestError):
        Manifest.from_dict({**base, "roles": {"CT": {"type": "volume", "pattern": "x"}}})
    with pytest.raises(pl.ManifestError, match="not valid JSON"):
        Manifest.from_json("{nope")


def test_labels_keys_become_ints():
    m = Manifest.from_dict(
        {
            "name": "x",
            "source": {"scheme": "local", "root": "."},
            "roles": {"mask": {"type": "labels", "pattern": "{id}.mha", "labels": {"1": "liver"}}},
        }
    )
    assert m.roles["mask"].labels == {1: "liver"}
    assert '"1": "liver"' in m.to_json()


def test_pattern_regex_and_derive_samples():
    rx, names = _pattern_regex("{id}/ct/*.dcm")
    assert names == ["id"] and rx.match("p01/ct/0001.dcm") and not rx.match("p01/mr/0001.dcm")
    m = Manifest.from_dict(
        {
            "name": "x",
            "source": {"scheme": "local", "root": "."},
            "pairing": "patient",
            "roles": {
                "ct": {"type": "volume", "pattern": "{id}/ct/*.dcm"},
                "mask": {"type": "labels", "pattern": "{id}/seg.nii.gz"},
                "mesh": {"type": "mesh", "pattern": "{id}/la.stl"},
            },
        }
    )
    listing = [
        "p01/ct/1.dcm",
        "p01/ct/2.dcm",
        "p01/seg.nii.gz",
        "p01/la.stl",
        "p02/ct/1.dcm",
        "p02/seg.nii.gz",
        "notes.txt",
    ]
    samples = derive_samples(m, listing)
    assert [s.id for s in samples] == ["p01", "p02"]
    assert samples[0].files == {
        "ct": "p01/ct",
        "mask": "p01/seg.nii.gz",
        "mesh": "p01/la.stl",
    }  # slices → folder
    assert samples[1].files == {"ct": "p02/ct/1.dcm", "mask": "p02/seg.nii.gz"}
    with pytest.raises(pl.ManifestError, match="no file in the source matches"):
        derive_samples(m, ["other/thing.ply"])


def test_load_manifest_errors():
    with pytest.raises(pl.ManifestError, match="No bundled manifest for hf://"):
        pl.data.load_manifest("hf://nobody/nothing")
    with pytest.raises(pl.ManifestError, match="hf://<org>/<name>"):
        pl.data.parse_hf_ref("hf://only-org")
    assert pl.data.parse_hf_ref("hf://org/name/a/b") == ("org/name", "a/b")
    assert pl.data.parse_hf_ref("hf://datasets/org/name") == ("org/name", None)
    with pytest.raises(FileNotFoundError, match="no bundled dataset"):
        pl.load("not_a_dataset_name")
