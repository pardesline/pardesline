"""PointNet semantic segmentation on hippocampus surfaces (anterior vs posterior).

    pip install "pardesline[all]" torch
    python examples/pointnet_hippocampus/run.py             # a few minutes on CPU

1. ``make_point_dataset.py`` turns the first 40 labelled MSD hippocampus cases
   into labelled point clouds (each label's surface sampled with normals).
2. ``pointnet_seg.py train`` fits the original PointNet segmentation network
   for a handful of epochs and ``eval`` reports per-class IoU on the held-out
   fraction. The reference scripts live in the ``pointnet-segmentation`` skill.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

HERE = Path(__file__).parent
data, out = HERE / "hippo_points", HERE / "runs"
run(
    "pointnet-segmentation",
    "make_point_dataset.py",
    "msd_task04_hippocampus",
    "--out",
    str(data),
    "--take",
    "40",
    "--points",
    "2048",
)
run(
    "pointnet-segmentation",
    "pointnet_seg.py",
    "train",
    "--data",
    str(data),
    "--epochs",
    "40",
    "--batch",
    "8",
    "--out",
    str(out),
)
run(
    "pointnet-segmentation", "pointnet_seg.py", "eval", "--data", str(data), "--weights", str(out / "best.pt")
)
