"""Dataset.export: a standard, self-describing copy of any dataset."""

from __future__ import annotations

import json

import numpy as np
import pytest

import pardesline as pl
from pardesline.data import DRAFT_NAME


def _source(tmp_path):
    root = tmp_path / "src"
    for pid in ("a", "b"):
        d = root / pid
        d.mkdir(parents=True)
        np.arange(16, dtype=np.float32).tofile(d / "sweep.bin")
        (d / "surface.stl").write_bytes(b"\0" * 20)
    return root


def test_export_materialises_arrays_and_writes_a_manifest(tmp_path):
    root = _source(tmp_path)
    ds = pl.load(
        root,
        license="CC-BY-4.0",
        types={"sweep": "points"},
        layout={"sweep": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},
        units="m",
        frame={"sweep": "sensor", "surface": "Z-up"},
    )
    assert not ds.is_draft
    out = tmp_path / "standard"
    m = ds.take(1).export(out)
    assert m.source.scheme == "local" and [s.id for s in m.samples] == ["a"]
    assert (out / "a" / "sweep.ply").is_file() and (out / "a" / "surface.stl").is_file()
    side = json.loads((out / "a" / "sweep.ply.pardesline.json").read_text())
    assert (
        side["kind"] == "pointcloud"
        and side["frame"]["axes"] == "sensor"
        and side["license"]["spdx"] == "CC-BY-4.0"
    )
    assert side["provenance"][0]["step"] == "load"
    assert (out / DRAFT_NAME).is_file()
    again = pl.load(out)  # reopens without a question
    assert len(again) == 1 and set(again[0].roles) == {"sweep", "surface"}
    cloud = again[0].sweep
    assert isinstance(cloud, pl.PointCloud) and cloud.extension == ".ply" and cloud.units == "m"
    assert again.license.spdx == "CC-BY-4.0"
    with pytest.raises(FileExistsError):
        ds.take(1).export(out)
    ds.export(out, overwrite=True)
    assert len(pl.load(out)) == 2
