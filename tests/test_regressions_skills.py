"""Regression tests for the scripts bundled in skills/ (2026-11 audit, additional findings).

"X-n" = docs/audit/2026-11-additional-findings.md. Synthetic data, no download.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

SKILLS = Path(__file__).resolve().parents[1] / "skills"


@pytest.mark.slow
@pytest.mark.local
def test_x10_pointnet_eval_and_inference_are_reproducible(tmp_path):
    """Evaluation subsampled points with an unseeded generator (mIoU 0.596 then 0.608 for the same
    weights), and inference padded its last chunk with random points whose predictions overwrote the
    labels of other chunks (7 of 1300 labels changed between runs)."""
    pytest.importorskip("torch")
    o3d = pytest.importorskip("open3d")
    script = SKILLS / "pointnet-segmentation" / "scripts" / "pointnet_seg.py"
    data = tmp_path / "data"
    data.mkdir()
    rng = np.random.default_rng(0)
    for i in range(8):
        p = rng.normal(size=(1200, 3))
        p /= np.linalg.norm(p, axis=1, keepdims=True)
        np.savez(
            data / f"s{i}.npz",
            points=np.hstack([p, p]).astype(np.float32),
            labels=(p[:, 1] > 0).astype(np.int64),
            classes=json.dumps({"0": "lower", "1": "upper"}),
        )

    def run(*args):
        proc = subprocess.run(
            [sys.executable, str(script), *map(str, args)], capture_output=True, text=True, timeout=900
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        return proc.stdout

    run("train", "--data", data, "--out", tmp_path / "run", "--epochs", 6, "--batch", 4, "--num-points", 512)
    weights = next((tmp_path / "run").glob("*.pt"))
    assert run("eval", "--data", data, "--weights", weights) == run(
        "eval", "--data", data, "--weights", weights
    )

    p = rng.normal(size=(1300, 3))
    p /= np.linalg.norm(p, axis=1, keepdims=True)
    pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(p))
    pc.normals = o3d.utility.Vector3dVector(p)
    o3d.io.write_point_cloud(str(tmp_path / "scan.ply"), pc)
    outputs = []
    for k in range(3):
        out = tmp_path / f"o{k}.ply"
        run("infer", "--weights", weights, "--input", tmp_path / "scan.ply", "--output", out)
        outputs.append(out.read_bytes())
    assert outputs[0] == outputs[1] == outputs[2]
