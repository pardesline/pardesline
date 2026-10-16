---
title: "PyVista Analysis (pyvista_analysis): 6 methods in Python"
description: "Geometric analysis and attribute computation via PyVista: curvature estimation, distance computation, glyph generation, vector magnitude, and scalar s"
---

# PyVista Analysis

`pyvista_analysis`: Geometric analysis and attribute computation via PyVista: curvature estimation, distance computation, glyph generation, vector magnitude, and scalar statistics.

| | |
|---|---|
| Methods | [`pv_curvature`](#pv_curvature), [`pv_distance`](#pv_distance), [`pv_glyph`](#pv_glyph), [`pv_vector_magnitude`](#pv_vector_magnitude), [`pv_scalar_stats`](#pv_scalar_stats), [`pv_extract_feature_edges`](#pv_extract_feature_edges) |
| Input files | `.ply`, `.obj`, `.stl`, `.vtk`, `.vtu` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| CLI | `pardesline run pyvista_analysis.<method> input.ext [--param value]` |

## How it works

PyVista analysis tools compute derived geometric quantities:

**Curvature** estimates surface curvature (mean, Gaussian, min, max) at each vertex.
**Distance** computes point-to-surface distances between two meshes.
**Glyphs** visualize vector fields by placing oriented symbols at data points.
**Vector Magnitude** computes $\|\mathbf{v}\|$ for each vector in a field.
**Scalar Statistics** provides summary statistics of scalar arrays.

## Methods

### pv_curvature

Curvature types: mean $H = \frac{\kappa_1 + \kappa_2}{2}$, Gaussian $K = \kappa_1 \kappa_2$, maximum $\kappa_1$, minimum $\kappa_2$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_analysis.pv_curvature")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_analysis.curvature --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `curvature_type` | string | `mean` |  | Curvature type: mean, gaussian, maximum, or minimum. | mean curvature is the one that reads as 'bumps and dents' on an organ or a part; Gaussian separates saddles, maximum/minimum are the principal curvatures. |

### pv_distance

Computes the closest-point distance from each vertex to a reference surface using a KD-tree.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_analysis.pv_distance")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_analysis.distance --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

No tunable parameters.

### pv_glyph

Creates oriented arrow glyphs at each point, scaled by a factor and oriented along a vector field.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_analysis.pv_glyph")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_analysis.glyph --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `scale_factor` | float | `0.01` | 0.0001 to 1.0 | Scale factor for glyph size. | 0.01 in file units draws normal arrows of 1 % of a unit object, visible without hiding the surface. |
| `vector_name` | string | `Normals` |  | Vector array to orient glyphs (e.g. Normals). | Normals is the array every mesh has after compute_normals. |
| `scale` *(advanced)* | bool | `false` |  | Scale glyphs by scalar/vector magnitude. | Off: all arrows the same length, so direction is what you see. |
| `tolerance` *(advanced)* | float | `-1.0` | -1.0 to 1.0 | Merge tolerance as fraction of bbox (-1 = auto/None). | -1 lets PyVista choose the glyph merge tolerance. |
| `absolute` *(advanced)* | bool | `false` |  | Interpret tolerance as an absolute distance. | Off: the tolerance is a fraction of the bounding box. |
| `clamping` *(advanced)* | bool | `false` |  | Clamp glyph scaling to the rng range. | Off: no scaling range clamp since scale is off. |

### pv_vector_magnitude

Computes $\|\mathbf{v}_i\| = \sqrt{v_{ix}^2 + v_{iy}^2 + v_{iz}^2}$ for each vector and stores as a scalar.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_analysis.pv_vector_magnitude")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_analysis.vector_magnitude --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `vector_name` | string | `Normals` |  | Name of the vector array to compute magnitude for. | Normals is the array every mesh has. |

### pv_scalar_stats

Computes min, max, mean, median, std, and stores a normalized version of the scalar array.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_analysis.pv_scalar_stats")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_analysis.scalar_stats --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `scalars` | string | `""` |  | Scalar array name (empty = first available). | Empty takes the first available array. |

### pv_extract_feature_edges

Extracts edges where the surface normal changes sharply. A feature edge is identified when the dihedral angle between adjacent faces exceeds the threshold. Also detects boundary edges (single-face adjacency) and non-manifold edges (three or more face adjacency).

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_analysis.pv_extract_feature_edges")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_analysis.extract_feature_edges --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `feature_angle` | float | `30.0` | 0.0 to 180.0 | Dihedral angle threshold for feature edge detection (degrees). | 30 degrees is VTK's default dihedral threshold: it catches machined edges and misses the facets of a smooth organ. |
| `boundary_edges` | string | `true` |  | Include boundary edges (true/false). | true: open boundaries are what you look for on a scan with holes. |
| `non_manifold_edges` | string | `true` |  | Include non-manifold edges (true/false). | true: non-manifold edges are the defects to fix before printing or simulation. |
| `manifold_edges` | string | `false` |  | Include regular manifold edges (true/false). | false: regular edges would be every edge of the mesh. |
| `feature_edges` *(advanced)* | bool | `true` |  | Include feature (sharp dihedral-angle) edges. | On: sharp edges are included. |
| `clear_data` *(advanced)* | bool | `false` |  | Drop point/cell data arrays from the output edges. | Off: keep the scalar arrays on the edges. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("pyvista_analysis")` prints this module from the installed package; `pl.describe("pyvista_analysis.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/pyvista_analysis.json` and `_defaults.json` on 2026-10-16.</sub>
