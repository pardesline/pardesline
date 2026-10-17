---
title: "PyVista Volume Processing (pyvista_volume_processing): 6 methods in Python"
description: "Volumetric and grid processing via PyVista: isosurface extraction (contouring), slicing, thresholding, geometry extraction, and cell filtering"
---

# PyVista Volume Processing

`pyvista_volume_processing`: Volumetric and grid processing via PyVista: isosurface extraction (contouring), slicing, thresholding, geometry extraction, and cell filtering.

| | |
|---|---|
| Methods | [`pv_contour`](#pv_contour), [`pv_slice`](#pv_slice), [`pv_slice_orthogonal`](#pv_slice_orthogonal), [`pv_threshold_volume`](#pv_threshold_volume), [`pv_extract_geometry`](#pv_extract_geometry), [`pv_extract_cells`](#pv_extract_cells) |
| Input files | `.vti`, `.vtk`, `.vtu`, `.ply`, `.obj`, `.stl` |
| Bundled datasets to try | [`open3d_bunny`](../datasets/open3d_bunny.md), [`open3d_icp_demo`](../datasets/open3d_icp_demo.md), [`kitti_raw_2011_09_26_drive_0001`](../datasets/kitti_raw_2011_09_26_drive_0001.md), [`medshapenet`](../datasets/medshapenet.md), [`c3vd_endoscopy_splats`](../datasets/c3vd_endoscopy_splats.md), [`hf_objaverse_glb_shard`](../datasets/hf_objaverse_glb_shard.md) |
| CLI | `pardesline run pyvista_volume_processing.<method> input.ext [--param value]` |

## How it works

PyVista volume processing wraps VTK filters for extracting information from volumetric and grid datasets:

**Contour/Isosurface** extracts surfaces at scalar isovalues using marching cubes.
**Slice** creates a cross-section along any plane.
**Threshold** selects cells within a scalar range.
**Extract Geometry** converts a volume to its surface representation.
**Extract Cells** selects cells by type.

## Methods

### pv_contour

Marching cubes extracts a surface mesh at scalar isovalue $c$: $\{\mathbf{x} : f(\mathbf{x}) = c\}$.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("pyvista_volume_processing.pv_contour")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_volume_processing.contour --input ... --output ...`.

**Defaults validated on:** MSD and RIRE volumes through Volume.to_mesh (examples/hippocampus_mask_to_mesh, examples/spleen_ct_threshold_segmentation); generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `n_contours` | int | `5` | 1 to 50 | Number of isosurface levels. | 5 evenly spaced iso-levels show the structure of an unknown field; a label map or a known threshold uses one level through Volume.to_mesh. |
| `scalars` | string | `""` |  | Scalar array name (empty = active scalars). | Empty uses the active scalars (the image intensity). |
| `compute_normals` *(advanced)* | bool | `false` |  | Compute point normals on the output surface. | Off: normals are recomputed later by the mesh steps that need them. |
| `compute_gradients` *(advanced)* | bool | `false` |  | Compute gradients at the isosurface. | Off: not needed for a surface. |
| `compute_scalars` *(advanced)* | bool | `true` |  | Preserve the contoured scalar on the output. | On: the contoured value is kept on the surface for colouring. |
| `method` *(advanced)* | enum | `contour` | `contour`, `marching_cubes`, `flying_edges` | Contouring algorithm. | contour is VTK's generic filter; marching_cubes and flying_edges are faster on image data and give the same surface. |
| `preference` *(advanced)* | enum | `point` | `point`, `cell` | Prefer point or cell scalars. | point: image intensities are point data. |

### pv_slice

Intersects the dataset with a plane $\mathbf{n} \cdot (\mathbf{x} - \mathbf{o}) = 0$ to produce a cross-section.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("pyvista_volume_processing.pv_slice")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_volume_processing.slice --input ... --output ...`.

**Defaults validated on:** RIRE and MSD volumes (README demo slices); generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `normal_x` | float | `1.0` | -1.0 to 1.0 | Slice normal X. | 1: an x-normal (sagittal in LPS) slice by default. |
| `normal_y` | float | `0.0` | -1.0 to 1.0 | Slice normal Y. | 0, see normal_x. |
| `normal_z` | float | `0.0` | -1.0 to 1.0 | Slice normal Z. | 0, see normal_x. |
| `origin_x` | float | `0.0` | -10000000000.0 to 10000000000.0 | Slice origin X (0 = center). | 0 means the volume centre. |
| `origin_y` | float | `0.0` | -10000000000.0 to 10000000000.0 | Slice origin Y (0 = center). | 0 means the centre. |
| `origin_z` | float | `0.0` | -10000000000.0 to 10000000000.0 | Slice origin Z (0 = center). | 0 means the centre. |
| `generate_triangles` *(advanced)* | bool | `false` |  | Triangulate the slice output. | Off: the slice stays a polygon mesh of quads. |
| `contour` *(advanced)* | bool | `false` |  | Generate contour edges of the slice. | Off: no contour edges. |

### pv_slice_orthogonal

Creates three orthogonal slices through the dataset at specified X, Y, Z positions.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("pyvista_volume_processing.pv_slice_orthogonal")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_volume_processing.slice_orthogonal --input ... --output ...`.

**Defaults validated on:** MSD hippocampus MRI (examples/hippocampus_mask_to_mesh); generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `x` | float | `0.0` | -10000000000.0 to 10000000000.0 | X position for YZ slice (0 = center). | 0 means the centre of the volume. |
| `y` | float | `0.0` | -10000000000.0 to 10000000000.0 | Y position for XZ slice (0 = center). | 0 means the centre. |
| `z` | float | `0.0` | -10000000000.0 to 10000000000.0 | Z position for XY slice (0 = center). | 0 means the centre. |
| `generate_triangles` *(advanced)* | bool | `false` |  | Triangulate the slice output. | Off: the slice stays a polygon mesh of quads, which renders and saves smaller. |
| `contour` *(advanced)* | bool | `false` |  | Generate contour edges of the slices. | Off: no contour edges are generated on the slice. |

### pv_threshold_volume

Selects cells with scalar values in $[l, u]$, preserving the volumetric structure.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("pyvista_volume_processing.pv_threshold_volume")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vtu`. Script: `python -m pardesline.ops.pyvista_volume_processing.threshold_volume --input ... --output ...`.

**Defaults validated on:** generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `lower` | float | `0.0` | -10000000000.0 to 10000000000.0 | Lower scalar bound. | 0 with upper 1 is a normalised placeholder; use Hounsfield units on CT. |
| `upper` | float | `1.0` | -10000000000.0 to 10000000000.0 | Upper scalar bound. | 1, see lower. |
| `scalars` *(advanced)* | string | `""` |  | Scalar array name (empty = active scalars). | Empty uses the active scalars. |
| `invert` *(advanced)* | bool | `false` |  | Invert the threshold selection. | Off: keep the inside of the range. |
| `continuous` *(advanced)* | bool | `false` |  | Use continuous cell range for thresholding. | Off: a cell is kept on its own scalar value, not on the range it spans. |
| `preference` *(advanced)* | enum | `cell` | `cell`, `point` | Prefer cell or point scalars. | cell: VTK's default. |
| `all_scalars` *(advanced)* | bool | `false` |  | Require all scalar components to satisfy the range. | Off: a cell is kept if any of its points pass, which keeps boundaries intact. |

### pv_extract_geometry

Extracts the boundary surface of a volume as a polygonal mesh.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("pyvista_volume_processing.pv_extract_geometry")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.ply`. Script: `python -m pardesline.ops.pyvista_volume_processing.extract_geometry --input ... --output ...`.

**Defaults validated on:** generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `extent` *(advanced)* | string | `""` |  | Optional crop extent 'xmin,xmax,ymin,ymax,zmin,zmax' (empty = full dataset). | Empty keeps the whole dataset; a six-number extent crops in index space. |

### pv_extract_cells

Selects cells matching a specified cell type (tetrahedral, hexahedral, etc.).

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("pyvista_volume_processing.pv_extract_cells")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vtu`. Script: `python -m pardesline.ops.pyvista_volume_processing.extract_cells --input ... --output ...`.

**Defaults validated on:** generated grids in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `cell_type` | string | `tetrahedral` |  | Cell type to extract: tetrahedral, hexahedral, wedge, pyramid, triangle, quad. | tetrahedral is the cell type of simulation meshes (VTU), the usual reason to extract by type. |
| `invert` *(advanced)* | bool | `false` |  | Invert selection (extract all cells NOT of this type). | Off: keep the named type. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("pyvista_volume_processing")` prints this module from the installed package; `pl.describe("pyvista_volume_processing.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/pyvista_volume_processing.json` and `_defaults.json` on 2026-10-17.</sub>
