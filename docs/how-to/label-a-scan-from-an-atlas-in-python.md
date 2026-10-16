---
title: How to label a scan from an atlas in Python (atlas-based segmentation of point clouds and meshes)
description: Transfer labels from a labelled atlas to an unlabelled 3D scan in Python: rigid registration with RANSAC + ICP, nearest-structure label transfer, per-label surfaces and volumes, and the agreement measured on a known case; the reference script and the one-liners behind it.
---

# How to label a scan from an atlas in Python

Atlas-based labelling: register a labelled reference shape (the atlas) onto a new scan, give each scan point the label of its nearest atlas structure, rebuild per-label surfaces. It works for ultrasound reconstructions, CBCT teeth, bones, LiDAR objects: anything where the anatomy or the part varies little between instances.

```python
import pardesline as pl

scan = pl.load("new_scan.ply")  # unlabelled, the fixed reference
atlas = pl.load("atlas.ply")  # labelled: one label per point, same order as a labels.npy
moved_atlas = scan.align(atlas)  # the atlas in the scan's frame; point order is kept
```

Labels travel with point order, so after registration the nearest atlas point to each scan point gives the label:

```python
import numpy as np
import open3d as o3d

labels = np.load("labels.npy")  # (N_atlas,) ints
tree = o3d.geometry.KDTreeFlann(moved_atlas.to_open3d())
scan_pts = scan.to_numpy()
scan_labels = np.array([labels[tree.search_knn_vector_3d(p, 1)[1][0]] for p in scan_pts])
```

Then per structure: `pl.load(...)` of the filtered points, `to_mesh()` for a surface, `to_pyvista().volume` for a volume.

## The reference script

[`atlas_label_transfer.py`](https://github.com/pardesline/pardesline/blob/main/skills/atlas-label-transfer/scripts/atlas_label_transfer.py) does all of it, with a tolerance on the transfer distance, per-label Poisson surfaces, volumes, and an evaluation against the truth when it is known. The [bunny example](../examples.md#atlas_label_transfer_bunny) runs it on a synthetic case: the bunny labelled into head, ears, body and base is the atlas; a rotated, noisy, sub-sampled copy is the scan; the transfer agrees with the truth on 99.4 % of the points with a 0.06° pose error.

```bash
python examples/atlas_label_transfer_bunny/run.py
python skills/atlas-label-transfer/scripts/atlas_label_transfer.py --atlas atlas.ply --atlas-labels labels.npy --scan scan.ply --out ./transfer
```

![Bunny atlas in grey with the scan coloured by transferred labels](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/atlas_label_transfer_bunny/atlas_transfer.png)

## When it fails

- Registration off: see [Fix ICP that does not converge](fix-icp-that-does-not-converge.md); on a symmetric atlas (a single tooth) add context (the arch).
- Labels bleed across boundaries: the transfer tolerance is too large for the point spacing; `--tolerance` in file units, about 2× the spacing.
- Shape differs (a bigger liver, a missing tooth): rigid cannot follow it; run `deformable_registration.cpd_deformable` after the rigid stage, then transfer.

Related: [Guide: atlas label transfer](../guides/atlas-label-transfer.md) · [Align two scans](align-two-scans-in-python.md) · [Evaluation metrics](../models/evaluation-metrics.md)
