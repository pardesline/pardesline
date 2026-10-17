---
title: "Voxelization & Volume (voxel_to_mesh): 2 methods in Python"
description: "Convert meshes and point clouds to voxel grids"
---

# Voxelization & Volume

`voxel_to_mesh`: Convert meshes and point clouds to voxel grids. Perform volumetric operations like binary erosion and marching cubes reconstruction.

| | |
|---|---|
| Methods | [`voxelization`](#voxelization), [`binary_erosion`](#binary_erosion) |
| Input files | `.ply`, `.obj`, `.stl`, `.off` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| CLI | `pardesline run voxel_to_mesh.<method> input.ext [--param value]` |

## How it works

Voxelization discretizes a 3D space into a regular grid of cubic cells (voxels). Each voxel stores a scalar value (occupancy, SDF, density). The inverse process extracts a surface mesh from this volumetric representation.

Marching Cubes is the standard iso-surface extraction algorithm. For each cube in the voxel grid, it classifies vertices as inside or outside the iso-surface based on their scalar values relative to an iso-value $\tau$.

Binary erosion shrinks a solid by removing boundary voxels using a structuring element.

## Methods

### voxelization

Voxelization converts a triangle mesh into a 3D occupancy grid. Open3D creates a VoxelGrid by testing which voxels intersect the mesh surface. The voxel size $v$ controls the resolution of the grid.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("voxel_to_mesh.voxelization")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.voxel_to_mesh.voxelization --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.01` | 0.002 to 0.05 | Size of each voxel cube. Smaller = more detail. | 0.01 in file units gives a 100-voxel grid across a unit-sized object: coarse enough to run in a second, fine enough to see shape; the range (0.002-0.05) assumes objects around a metre, so scale it for millimetre data. |

### binary_erosion

Binary erosion shrinks a solid by removing boundary voxels. For a volume $V$ and structuring element $B$:
$$V \ominus B = \{x : B_x \subseteq V\}$$
The eroded volume is then reconstructed back to a mesh using marching cubes at iso-value 0.5.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("voxel_to_mesh.binary_erosion")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.voxel_to_mesh.binary_erosion --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `voxel_size` | float | `0.01` | 0.002 to 0.05 | Voxel size for the occupancy grid. | Same grid as voxelization so the two can be compared on the same object. |
| `erosion_iterations` | int | `1` | 1 to 5 | Number of erosion iterations. | 1 iteration removes one voxel layer: the thinnest shell, which is what you want to strip surface noise without eating thin parts. |
| `erosion_connectivity` *(advanced)* | int | `1` | 1 to 3 | Connectivity of the 3D structuring element (1=faces, 2=+edges, 3=+corners). | 1 (faces only) is the most conservative structuring element: each iteration removes the least material. |
| `iso_level` *(advanced)* | float | `0.5` | 0.0 to 1.0 | Marching-cubes iso-surface level. | 0.5 is the half-occupancy surface of a binary grid: the boundary between inside and outside voxels. |
| `padding_voxels` *(advanced)* | int | `5` | 0 to 50 | Padding added around the bounding box, expressed in voxels. | 5 voxels of margin keep marching cubes from clipping the surface at the grid border. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("voxel_to_mesh")` prints this module from the installed package; `pl.describe("voxel_to_mesh.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/voxel_to_mesh.json` and `_defaults.json` on 2026-10-10.</sub>
