---
title: "PointNet segmentation of medical and industrial point clouds in Python"
description: "Expert guide to PointNet and PointNet++ for per-point semantic segmentation of medical and industrial point clouds (CBCT teeth, bones, organs sampled from "
---

# PointNet segmentation of medical and industrial point clouds in Python

!!! info "What ships today, and what is coming"
    **Today:** `make_point_dataset.py` (label surfaces to labelled point clouds) and `pointnet_seg.py` (train / eval / infer, the original PointNet segmentation network). No weights are shipped and there is no inference API: the scripts are reference implementations that read any pardesline dataset.

    **Coming: one-line model access.** The same registry pattern as datasets, a model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model(...)` / `pl.run(model, dataset)`. This page keeps its URL. Follow and vote on the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22); model manifests can be contributed now from [`templates/new_model/`](https://github.com/pardesline/pardesline/tree/main/templates/new_model).

**Reference scripts:** [`make_point_dataset.py`](https://github.com/pardesline/pardesline/blob/main/skills/pointnet-segmentation/scripts/make_point_dataset.py), [`pointnet_seg.py`](https://github.com/pardesline/pardesline/blob/main/skills/pointnet-segmentation/scripts/pointnet_seg.py) (shipped in the wheel under `pardesline/skills/pointnet-segmentation/scripts/`, served by the MCP tool `get_skill`).

**Runnable example:** [`examples/pointnet_hippocampus/run.py`](https://github.com/pardesline/pardesline/tree/main/examples/pointnet_hippocampus), executed on 2026-10-16; its outputs are committed next to it.

# PointNet / PointNet++ segmentation

## Architecture (segmentation branch), tensor by tensor

```
input           (N x 3)    xyz, optionally (N x 6) with normals
T-Net(3)        3 x 3      mini-PointNet regresses a transform; x <- x @ T          input alignment
shared MLP      (N x 64) -> (N x 64)                                                 per-point, Conv1d k=1
T-Net(64)       64 x 64    + regulariser L_reg = || I - A A^T ||_F^2 (weight 1e-3)  feature alignment
shared MLP      (N x 64) -> (N x 128) -> (N x 1024)
max-pool        (1 x 1024)  symmetric function: order-invariant global descriptor
broadcast+concat (N x 1088) = local 64-d  ++  global 1024-d                          every point sees the shape
seg head        (N x 512) -> (N x 256) -> (N x 128) -> (N x K)  softmax per point
```

Why it works: a shared MLP applied per point followed by a **symmetric**
pooling is invariant to the point order (`f({x_i}) = gamma(max_i h(x_i))`);
the T-Nets learn a canonical pose so the network does not have to see every
rotation; the global feature acts as context memory for each point. What it
cannot do: capture local neighbourhoods (two points 1 mm apart are processed
independently until the global pooling), hence boundaries between adjacent
teeth or vertebrae come out ragged.

**PointNet++** fixes that with set-abstraction levels: farthest-point
sampling of centroids, ball query (radius r) grouping, a mini-PointNet per
group, repeated 3 times with growing radii (0.1 / 0.2 / 0.4 in the unit
sphere), then feature propagation (interpolation + skip links) back to all
points for segmentation. Multi-scale grouping (MSG) uses several radii per
level for density robustness. Modern successors (Point Transformer v3, PointNeXt)
keep the same data contract; start with PointNet++ unless you have 10 k+
labelled clouds.

## Data contract

| Item | Value |
|---|---|
| Points per cloud | 2048 (parts, teeth) to 4096-8192 (organs, scenes); sample with FPS or Poisson-disk, pad by repetition |
| Features | xyz; add normals (N x 6) for surfaces, intensity for LiDAR, HU for CT-derived points |
| Normalisation | subtract the centroid, divide by the max radius (unit sphere) per cloud; **store the scale and centroid** to map predictions back |
| Labels | one integer per point, 0..K-1, with a class table; `-1` = ignore |
| Augmentation | random rotation about the up axis (or full SO(3) when poses are arbitrary), jitter sigma 0.01 clipped at 0.05, random scale 0.8-1.25, point dropout |
| Split | by patient / object, never by cloud of the same object |

### Labelled clouds from pardesline datasets

[`scripts/make_point_dataset.py`](https://github.com/pardesline/pardesline/blob/main/skills/pointnet-segmentation/scripts/make_point_dataset.py) turns any dataset with label roles into
`.npz` training clouds: for each sample it extracts the surface of each label
(`LabelMap.to_mesh(label=k)`), samples it (`Mesh.to_points`, Poisson-disk,
face normals), tags the points with `k`, merges the structures, normalises,
and writes `points (N,6) float32, labels (N,) int64, centroid, scale, frame`.
Works on `msd_task04_hippocampus` (anterior / posterior), `amos22` (15
organs), `totalsegmentator_ct` (pick the organ roles), `verse19_spine`
(vertebra ids), `medshapenet` meshes (one structure per file: label by file),
and your own folder after `pl.scan`. CBCT teeth: segment the arch with
`simpleitk_segmentation.manual_threshold` on HU, `LabelMap.to_mesh`, then
label points by tooth from an existing annotation.

## Training recipe

- Loss: cross-entropy with class weights `1 / log(1.2 + freq)` (or Dice +
  CE) plus `1e-3 * L_reg`; label smoothing 0.1 helps on noisy boundaries.
- Adam lr 1e-3, batch 16-32, 200 epochs, lr x0.5 every 20 epochs (or cosine);
  batch-norm momentum decayed; dropout 0.5 before the last layers.
- Mixed precision is fine; a 2048-point PointNet trains in ~1 h on one GPU
  for 5 k clouds.
- Monitor per-class IoU on a patient-level validation split; mIoU is the
  headline, the smallest class is the story.
- Pretrained weights (ShapeNet part segmentation) help only for the first
  epochs; medical shapes differ enough that training from scratch with
  augmentation is usually as good.

[`scripts/pointnet_seg.py`](https://github.com/pardesline/pardesline/blob/main/skills/pointnet-segmentation/scripts/pointnet_seg.py) is a complete PyTorch reference (model, dataset
loader for the `.npz` contract, training loop, evaluation, inference that
writes a labelled PLY readable by pardesline). It needs `torch`.

## Evaluation

Per-class IoU and mIoU on points; because sampling is uniform, points-IoU
approximates surface-area IoU. Add a **boundary error**: fraction of
mislabelled points within 1 mm of a label boundary vs away from it, to
distinguish "ragged edges" from "wrong structure". For volumes of structures
(teeth, chambers): reconstruct per label (`atlas-label-transfer` skill) and
compare volumes.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| mIoU stuck ~ majority class | class imbalance, lr too high | class weights, Dice term, lr 1e-4 warm-up |
| Rotated test clouds fail | training poses too uniform; T-Net not enough | full SO(3) augmentation, or canonicalise with PCA / a registration step before the network |
| Ragged boundaries between neighbours | no local features (PointNet) | PointNet++ / k-NN graph, add normals, post-process by majority vote in a 1 mm neighbourhood |
| Good on train, bad on new scanner | density / noise shift | voxel-downsample to a fixed spacing before sampling, noise augmentation |
| Tiny structures vanish | 2048 points too few for them | more points, or crop per region, or oversample points on small classes |

## Inference back to objects

```python
import numpy as np, pardesline as pl

cloud = pl.load("arch.ply").with_frame("LPS", "mm")
xyz = cloud.to_numpy()  # (N,3)
# ... normalise, forward, argmax -> labels (N,)
from pardesline.object.arrays import write_ply

out = pl.load(write_ply("arch_labelled.ply", xyz, {"label": labels}))  # label as a per-point property
```

Datasets: `msd_task04_hippocampus`, `amos22`, `totalsegmentator_ct`,
`verse19_spine`, `medshapenet`, `hf_kitti360_gs_subset` (`points` +
`point_segments` for scene segmentation), `kitti_raw_2011_09_26_drive_0001`.

<sub>Source: `skills/pointnet-segmentation/SKILL.md`, published on 2026-10-16.</sub>
