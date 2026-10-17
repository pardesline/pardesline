---
title: "PyVista Mesh Processing (pyvista_mesh_processing): 9 methods in Python"
description: "Mesh geometry operations powered by PyVista/VTK: decimation, subdivision, smoothing (Laplacian, Taubin), cleaning, hole filling, normal computation, t"
---

# PyVista Mesh Processing

`pyvista_mesh_processing`: Mesh geometry operations powered by PyVista/VTK: decimation, subdivision, smoothing (Laplacian, Taubin), cleaning, hole filling, normal computation, triangulation, and surface extraction.

| | |
|---|---|
| Methods | [`pv_decimate`](#pv_decimate), [`pv_subdivide`](#pv_subdivide), [`pv_smooth_laplacian`](#pv_smooth_laplacian), [`pv_smooth_taubin`](#pv_smooth_taubin), [`pv_clean`](#pv_clean), [`pv_fill_holes`](#pv_fill_holes), [`pv_compute_normals`](#pv_compute_normals), [`pv_triangulate`](#pv_triangulate), [`pv_extract_surface`](#pv_extract_surface) |
| Input files | `.ply`, `.obj`, `.stl`, `.vtk`, `.vtu` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| Example | [Label map to mesh on MSD hippocampus](../examples.md#hippocampus_mask_to_mesh) |
| CLI | `pardesline run pyvista_mesh_processing.<method> input.ext [--param value]` |

## How it works

PyVista wraps VTK filters for mesh geometry processing. Operations include:

**Decimation** reduces triangle count using quadric error metrics.
**Subdivision** refines meshes by splitting triangles (linear, butterfly, loop).
**Smoothing** removes noise via Laplacian $\mathbf{v}_i' = \mathbf{v}_i + \lambda \Delta \mathbf{v}_i$ or Taubin's $\lambda|\mu$ scheme.
**Cleaning** merges duplicate points and removes degenerate cells.
**Triangulation** converts polygonal cells to triangles.

## Methods

### pv_decimate

Reduces mesh complexity by collapsing edges based on quadric error metrics. Target reduction is a fraction $r \in [0,1)$ of triangles to remove.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_decimate")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.decimate --input ... --output ...`.

**Defaults validated on:** MSD hippocampus surfaces (examples/hippocampus_mask_to_mesh, decimate 0.5); generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `target_reduction` | float | `0.5` | 0.01 to 0.99 | Fraction of triangles to remove (0.5 = remove 50%). | 0.5 halves the triangle count: on marching-cubes output (one triangle per voxel face) that removes the redundant co-planar triangles with no visible change. |
| `volume_preservation` *(advanced)* | bool | `false` |  | Constrain decimation to preserve mesh volume (slower, less shrinkage). | Off: VTK's default; on when the mesh is used for volume measurements (organs), since plain quadric decimation shrinks convex shapes slightly. |
| `attribute_error` *(advanced)* | bool | `false` |  | Include scalar/attribute error in the decimation cost metric. | Off: ignore scalar fields in the error metric; on when a label or curvature field must survive decimation. |
| `normals` *(advanced)* | bool | `false` |  | Include normals deviation in the decimation cost metric. | Off: do not penalise normal deviation; on for CAD meshes with sharp edges. |
| `boundary_constraints` *(advanced)* | bool | `false` |  | Use legacy boundary-edge-length weighting for boundary quadric constraints. | Off: VTK's current boundary handling; the legacy weighting is for reproducing old results. |

### pv_subdivide

Refines mesh by splitting triangles. Linear splits at midpoints; butterfly and loop use interpolation for smoother results.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_subdivide")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.subdivide --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `n_subdivisions` | int | `1` | 1 to 4 | Number of subdivision iterations. | 1 iteration quadruples the triangle count, which is as much as a smoothing or sampling step ever needs. |
| `algorithm` | string | `linear` |  | Subdivision algorithm: linear, butterfly, or loop. | linear keeps the surface exactly where it is and only adds vertices; butterfly and loop also smooth, which changes the geometry. |

### pv_smooth_laplacian

Iteratively moves each vertex toward the centroid of its neighbors: $\mathbf{v}_i' = \mathbf{v}_i + \lambda \frac{1}{|N_i|} \sum_{j \in N_i}(\mathbf{v}_j - \mathbf{v}_i)$.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_smooth_laplacian")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.smooth_laplacian --input ... --output ...`.

**Defaults validated on:** MSD hippocampus surfaces (examples/hippocampus_mask_to_mesh); generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `n_iterations` | int | `20` | 1 to 500 | Number of smoothing iterations. | 20 iterations remove the voxel staircase of a marching-cubes surface; more than 50 visibly shrinks small structures. |
| `relaxation_factor` | float | `0.01` | 0.001 to 1.0 | Step size per iteration (higher = more smoothing). | 0.01 is VTK's default step: small steps over 20 iterations move vertices by less than a voxel in total. |
| `convergence` *(advanced)* | float | `0.0` | 0.0 to 1.0 | Convergence threshold; smaller = more iterations. 0 disables early stop. | 0 disables early stop so the iteration count is the only knob. |
| `edge_angle` *(advanced)* | float | `15.0` | 0.0 to 180.0 | Edge angle (deg) for interior edge features when feature_smoothing is on. | 15 degrees is VTK's edge-feature threshold when feature smoothing is on. |
| `feature_angle` *(advanced)* | float | `45.0` | 0.0 to 180.0 | Feature angle (deg) for sharp-feature detection when feature_smoothing is on. | 45 degrees is VTK's sharp-feature threshold when feature smoothing is on. |
| `boundary_smoothing` *(advanced)* | bool | `true` |  | Allow boundary (edge) vertices to move during smoothing. | On: boundary vertices of open surfaces move too, otherwise the rim stays jagged. |
| `feature_smoothing` *(advanced)* | bool | `false` |  | Smooth along detected sharp features rather than freezing them. | Off: organic surfaces have no sharp features to preserve; on for CAD parts. |

### pv_smooth_taubin

Alternates shrinking ($\lambda > 0$) and inflating ($\mu < 0$) steps to smooth without volume shrinkage. Pass-band controls the cutoff frequency.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_smooth_taubin")  # catalog defaults
# same thing, domain vocabulary: `mesh.smooth()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.smooth_taubin --input ... --output ...`.

**Defaults validated on:** MSD hippocampus surfaces: the default mesh.smooth() (examples/hippocampus_mask_to_mesh); generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `n_iterations` | int | `20` | 1 to 500 | Number of smoothing iterations. | 20 iterations remove the voxel staircase; Taubin's pass band keeps the volume, so the count can be higher than for Laplacian smoothing without shrinkage. |
| `pass_band` | float | `0.1` | 0.001 to 2.0 | Pass-band value controlling cutoff frequency. | 0.1 is VTK's default: frequencies above it are attenuated (staircase), below it kept (anatomy); lower it for a smoother result. |
| `edge_angle` *(advanced)* | float | `15.0` | 0.0 to 180.0 | Edge angle (deg) for interior edge features when feature_smoothing is on. | 15 degrees, VTK's edge-feature threshold. |
| `feature_angle` *(advanced)* | float | `45.0` | 0.0 to 180.0 | Feature angle (deg) for sharp-feature detection when feature_smoothing is on. | 45 degrees, VTK's sharp-feature threshold. |
| `boundary_smoothing` *(advanced)* | bool | `true` |  | Allow boundary (edge) vertices to move during smoothing. | On so open rims are smoothed too. |
| `feature_smoothing` *(advanced)* | bool | `false` |  | Smooth along detected sharp features rather than freezing them. | Off for organic surfaces. |
| `non_manifold_smoothing` *(advanced)* | bool | `false` |  | Also smooth non-manifold vertices. | Off: non-manifold vertices (two sheets touching) are left in place to avoid tearing. |
| `normalize_coordinates` *(advanced)* | bool | `false` |  | Normalize coordinates before smoothing for better numerical stability. | Off: VTK's default; on for coordinates with very large magnitudes (UTM metres) to keep the filter numerically stable. |

### pv_clean

Merges coincident points, removes degenerate cells, and strips unused points within the specified tolerance.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_clean")  # catalog defaults
# same thing, domain vocabulary: `mesh.clean()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.clean --input ... --output ...`.

**Defaults validated on:** every Mesh.clean() in the examples; generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `tolerance` | float | `0.0` | 0.0 to 1.0 | Merge tolerance (0 = exact duplicates only). | 0 merges exact duplicates only: safe on any mesh; a positive tolerance welds nearby vertices and can close scan seams. |
| `point_merging` *(advanced)* | bool | `true` |  | Merge coincident points within tolerance. | On: duplicate vertices from STL files and marching cubes are merged. |
| `absolute` *(advanced)* | bool | `true` |  | Interpret tolerance as an absolute distance (else fraction of bounding box). | On: the tolerance is in file units, not a fraction of the bounding box, so it means the same thing on every mesh. |
| `lines_to_points` *(advanced)* | bool | `true` |  | Convert degenerate lines (zero length) to points. | On: zero-length lines become points instead of invalid cells. |
| `polys_to_lines` *(advanced)* | bool | `true` |  | Convert degenerate polygons to lines. | On: degenerate polygons become lines. |
| `strips_to_polys` *(advanced)* | bool | `true` |  | Convert degenerate triangle strips to polygons. | On: degenerate strips become polygons. |

### pv_fill_holes

Identifies boundary edges and fills holes smaller than the specified size by generating new triangular faces.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_fill_holes")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.fill_holes --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `hole_size` | float | `100.0` | 1.0 to 10000.0 | Maximum hole size to fill. | 100 in file units is the largest hole (by boundary radius) that is filled: scan holes, not the open bottom of a bust. |

### pv_compute_normals

Computes point and cell normals from triangle geometry. Consistency flips normals to face outward.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_compute_normals")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.compute_normals --input ... --output ...`.

**Defaults validated on:** generated meshes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `flip_normals` | int | `0` | 0 to 1 | Flip all normals (0=no, 1=yes). | 0: keep the file's orientation. |
| `consistency` | int | `1` | 0 to 1 | Enforce consistent normal orientation (0=no, 1=yes). | 1: make neighbouring faces agree, which STL files from scanners often do not. |
| `cell_normals` *(advanced)* | bool | `true` |  | Compute per-cell (face) normals. | On: per-face normals for rendering and sampling. |
| `point_normals` *(advanced)* | bool | `true` |  | Compute per-point (vertex) normals. | On: per-vertex normals for smooth shading and registration. |
| `split_vertices` *(advanced)* | bool | `false` |  | Split vertices along sharp edges (creates duplicate points at hard edges). | Off: splitting duplicates vertices along sharp edges and breaks the connectivity other steps rely on. |
| `auto_orient_normals` *(advanced)* | bool | `false` |  | Automatically orient normals outward (assumes a closed manifold). | Off: it assumes a closed manifold and inverts open scans. |
| `non_manifold_traversal` *(advanced)* | bool | `true` |  | Prevent orientation propagation across non-manifold edges. | On: orientation does not propagate across non-manifold edges, where it would flip. |
| `feature_angle` *(advanced)* | float | `30.0` | 0.0 to 180.0 | Feature angle (deg) used when split_vertices is on. | 30 degrees when split_vertices is on, VTK's default. |

### pv_triangulate

Converts all polygonal cells (quads, n-gons) into triangles for uniform processing.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_triangulate")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.triangulate --input ... --output ...`.

**Defaults validated on:** every Volume.to_mesh() surface is triangulated before saving (examples/hippocampus_mask_to_mesh); generated meshes in tests/test_ops_smoke.py

No tunable parameters.

### pv_extract_surface

Extracts the outer surface of a volumetric or unstructured grid as a polygonal mesh.

```python
import pardesline as pl

obj = pl.load("input.ply")
result = obj.run("pyvista_mesh_processing.pv_extract_surface")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_mesh_processing.extract_surface --input ... --output ...`.

**Defaults validated on:** every Volume.to_mesh() result goes through surface extraction (examples/hippocampus_mask_to_mesh); generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `pass_pointid` *(advanced)* | bool | `true` |  | Keep original point ids as a 'vtkOriginalPointIds' array on the surface. | On: keep the original point ids so results can be mapped back to the volume. |
| `pass_cellid` *(advanced)* | bool | `true` |  | Keep original cell ids as a 'vtkOriginalCellIds' array on the surface. | On: keep the original cell ids for the same reason. |
| `nonlinear_subdivision` *(advanced)* | int | `1` | 0 to 4 | Subdivision level for nonlinear (higher-order) cells; 1 matches the default. | 1 matches VTK's default for higher-order cells; the grids here are linear. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("pyvista_mesh_processing")` prints this module from the installed package; `pl.describe("pyvista_mesh_processing.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/pyvista_mesh_processing.json` and `_defaults.json` on 2026-10-10.</sub>
