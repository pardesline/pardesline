---
title: How to load raw .npy and .bin point clouds with a layout (KITTI Velodyne, npz grids)
description: Read headerless KITTI .bin sweeps, .npy arrays and .npz occupancy grids as point clouds and volumes in Python by declaring a layout (dtype, shape, columns, key) instead of guessing; convert to PLY and MetaImage.
---

# How to load raw `.npy` and `.bin` point clouds with a layout

A `.bin` file is numbers. Only you know that KITTI's are `float32 (N, 4)` with `x, y, z, reflectance` in the sensor frame in metres. pardesline refuses to guess and takes a **layout**:

```python
import pardesline as pl

sweep = pl.load(
    "0000000000.bin",
    layout={"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "reflectance"]},
).with_frame("sensor", "m")
print(sweep.kind, sweep.to_numpy().shape)  # pointcloud (N, 3)
sweep.save("sweep.ply")  # PLY with reflectance as a property + sidecar with the layout
```

A `(N,k)` shape is points, an `(a,b,c)` shape is a grid; `kind="volume"` or `kind="labels"` forces it. For `.npz`, `key=` picks the array; `allow_pickle` stays off.

```python
occ = pl.load(
    "frame.npz",
    layout={"key": "occ_label", "shape": "(200,200,16)", "spacing": [0.4, 0.4, 0.4]},
    kind="labels",
)
occ = occ.with_labels({0: "free", 1: "car", 2: "pedestrian"})
occ.to_mesh(label=1).save("cars.ply")
```

## In a manifest, once for the whole dataset

The bundled KITTI manifest declares the layout on the role, so every sweep opens without arguments:

```python
drive = pl.load("kitti_raw_2011_09_26_drive_0001")
frame = next(s for s in drive if "lidar" in s.roles)
sweep = frame.lidar  # (N, 4) decoded through the manifest layout, sensor frame, metres
objects = sweep.run("lidar_scene_detection.object_clustering")
```

For your own folder of `.bin` files, `pl.scan(folder)` asks for the layout as a question; answer with `layout={"lidar": {...}}` or edit the manifest.

## Checks

- Point count: `len(file) / (4 * 4)` must be an integer for `float32 (N,4)`; otherwise the dtype or the column count is wrong.
- Scale: KITTI ranges reach 80 m; if `to_numpy().max()` is 80 000 the file is in millimetres.
- Order: `order="F"` for Fortran-ordered grids (MATLAB exports).

Related: [KITTI raw manifest](../datasets/kitti_raw_2011_09_26_drive_0001.md) · [UniOcc occupancy grids](../datasets/hf_uniocc_carla_mini.md) · [Concepts: object](../getting-started/concepts.md#object)
