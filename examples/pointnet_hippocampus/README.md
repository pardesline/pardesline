# PointNet semantic segmentation on hippocampus surfaces (anterior vs posterior)

| | |
|---|---|
| Dataset | `msd_task04_hippocampus` |
| What it shows | 40 labelled cases to point clouds (2 048 points, normals), PointNet trained 40 epochs: 0.97 mIoU, 0.98 accuracy on the held-out fraction. |
| Extra dependencies | torch |
| Cold runtime (Windows laptop, CPU) | 6 min |

1. ``make_point_dataset.py`` turns the first 40 labelled MSD hippocampus cases
   into labelled point clouds (each label's surface sampled with normals).
2. ``pointnet_seg.py train`` fits the original PointNet segmentation network
   for a handful of epochs and ``eval`` reports per-class IoU on the held-out
   fraction. The reference scripts live in the ``pointnet-segmentation`` skill.

```bash
pip install "pardesline[all]" torch
python examples/pointnet_hippocampus/run.py             # a few minutes on CPU
```

Outputs are written next to this file; `result.json` and the images are committed, large files are ignored. See [`examples/README.md`](../README.md) for the full gallery.
