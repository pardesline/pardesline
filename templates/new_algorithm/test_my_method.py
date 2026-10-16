"""Smoke test for <module>.my_method on generated data (copy to tests/ and rename)."""

import numpy as np
import pytest

import pardesline as pl
from pardesline.object.arrays import write_ply

pytestmark = pytest.mark.local  # needs the [local] extra


def test_my_method_runs_and_records_the_step(tmp_path):
    rng = np.random.default_rng(0)
    pts = rng.normal(size=(2000, 3)) * 0.1
    src = tmp_path / "cloud.ply"
    write_ply(src, pts)
    out = pl.load(src).run("<module>.my_method", radius=0.05)
    assert out.path.is_file() and out.kind == "pointcloud"
    step = out.provenance[-1]
    assert step["method"] == "my_method" and step["params"] == {"radius": "0.05"}
    assert out.transform is None or isinstance(out.transform, dict)
