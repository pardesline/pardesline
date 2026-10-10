# PardesLine

**3D vision and medical imaging in one Python package.** 73 algorithms on point
clouds, meshes and volumes, with a typed catalog of 371 parameters, that run on
your machine with `pip install pardesline` — the same code that powers the
[PardesLine platform](https://appbeta.pardesline.com).

```python
import pardesline as pl

scan = pl.load("scan.ply")  # a local point cloud
surface = scan.downsample(voxel_size=0.01).remove_outliers().normals().poisson(depth=9)
surface.save("surface.ply")

# any of the 73 methods, by name, with validated parameters
res = pl.run("simpleitk_registration", "rigid", "ct.mha", moving="mr.mha", num_iterations=200)
print(res.output, res.sidecar)  # registered volume + transform JSON
```

> **Status: 0.2.0 alpha.** Local execution, the catalog and the cloud client
> are stable and tested on Linux, Windows and macOS. Dataset loaders
> (`pl.load("hf://…")`), the typed object model with frames, units and labels,
> and the local MCP server are the next milestones — see [Roadmap](#roadmap).

## Install

```bash
pip install "pardesline[all]"        # everything: Open3D, PyVista, SimpleITK
pip install "pardesline[local]"      # point clouds, meshes, SDF, LiDAR (Open3D, PyVista)
pip install "pardesline[medical]"    # volumes, DICOM, registration, segmentation (SimpleITK)
pip install pardesline               # catalog + object model + cloud client only
```

Python 3.10 – 3.12 for the native extras (Open3D 0.19 has no 3.13 wheels);
the core package also runs on 3.13.

## What you get

| | |
|---|---|
| **`pl.load(path)`** | Opens a local file as a typed `Object` (point cloud, mesh, volume, transform, image). |
| **`obj.run("module.method", **params)`** | Runs any algorithm on it and returns a new `Object` with provenance. Friendly aliases: `downsample`, `remove_outliers`, `normals`, `poisson`, `ball_pivoting`, `decimate`, `smooth`, `to_points`, `icp`, `ransac`, `register`, `segment`. |
| **`pl.run(module, method, input, **params)`** | The same without the object wrapper. Returns output path, sidecar JSON, log and timing. |
| **`pl.catalog()`** | Every module, method and parameter with type, default, range, choices and description. `pl.describe("point_cloud_reconstruction.poisson")`. |
| **`obj.to_open3d()` / `to_pyvista()` / `to_sitk()`** | Hand the result to the library you already use. `pl.o3d`, `pl.pv`, `pl.sitk` are the real libraries when installed. |
| **`pardesline` CLI** | `pardesline list`, `pardesline describe …`, `pardesline run module.method in.ply -o out.ply --voxel_size 0.02`. |
| **`pardesline.medical`** | Volume I/O (NIfTI, NRRD, MHA, VTI, DICOM series), rigid / affine / B-spline / demons registration, thresholding, watershed, connected components. |
| **`pardesline.cloud`** | The hosted platform: upload, share in one line, run on GPU, open the browser viewers. Optional, needs an account. |

Every algorithm is also a plain command with the same contract the platform uses:

```bash
python -m pardesline.ops.point_cloud_processing.voxel_downsample --input scan.ply --output small.ply --voxel_size 0.02
```

Parameters are checked **before** anything runs — unknown names, wrong types,
out-of-range values and missing second inputs fail with a message that lists
what is accepted:

```
ParameterError: point_cloud_processing.voxel_downsample: unknown parameter(s) voxel.
Did you mean: voxel -> voxel_size?. Accepted: voxel_size.
```

## The catalog

| Module | Methods | Input |
|---|---|---|
| `point_cloud_processing` | voxel_downsample, statistical_outlier_removal, radius_outlier_removal, mesh_to_pointcloud | .ply, .pcd, .txt, .xyz |
| `mesh_processing` | subdivision, simplification, mesh_to_pcd_uniform, mesh_to_pcd_poisson_disk | .ply, .obj, .stl, .off |
| `voxel_to_mesh` | voxelization, binary_erosion | .ply, .obj, .stl, .off |
| `sdf` | compute_sdf, occupancy_reconstruction, sdf_voxel_visualization | .ply, .obj, .stl, .off |
| `point_cloud_reconstruction` | poisson, convex_hull, alpha_shape, ball_pivoting | .ply, .pcd, .txt, .xyz |
| `registration` | ransac_global, icp_refinement, ransac_icp_pipeline | .ply, .pcd, .txt, .xyz |
| `deformable_registration` | cpd_deformable, gaussian_deformation | .ply, .pcd, .txt, .xyz |
| `point_cloud_segmentation` | ransac_plane, dbscan_clustering | .ply, .pcd, .txt, .xyz |
| `stereo_3d_reconstruction` | depth_colorization, depth_filter | .ply, .pcd, .txt, .xyz |
| `lidar_scene_detection` | height_colorization, ground_removal, object_clustering | .ply, .pcd, .txt, .xyz, .las |
| `lidar_camera_fusion` | intensity_colorization, roi_extraction, multi_resolution | .ply, .pcd, .txt, .xyz, .las |
| `features_extraction` | normal_estimation, fpfh_features, curvature_estimation | .ply, .pcd, .txt, .xyz |
| `collision_detection` | sdf_collision, penetration_depth | .ply, .obj, .stl, .off |
| `pyvista_mesh_processing` | pv_decimate, pv_subdivide, pv_smooth_laplacian, pv_smooth_taubin, pv_clean, pv_fill_holes, pv_compute_normals, pv_triangulate, pv_extract_surface | .ply, .obj, .stl, .vtk, .vtu |
| `pyvista_pointcloud_processing` | pv_threshold, pv_clip_plane, pv_clip_box, pv_random_sample, pv_extract_points | .ply, .pcd, .vtk, .vtu, .obj, .stl |
| `pyvista_volume_processing` | pv_contour, pv_slice, pv_slice_orthogonal, pv_threshold_volume, pv_extract_geometry, pv_extract_cells | .vti, .vtk, .vtu, .ply, .obj, .stl |
| `pyvista_analysis` | pv_curvature, pv_distance, pv_glyph, pv_vector_magnitude, pv_scalar_stats, pv_extract_feature_edges | .ply, .obj, .stl, .vtk, .vtu |
| `simpleitk_registration` | rigid, advanced_rigid, affine, bspline, demons, difference_analysis | .vti, .mha, .nrrd, .nii, .dcm |
| `simpleitk_segmentation` | otsu_threshold, manual_threshold, connected_components, watershed | .vti, .mha, .nrrd, .nii |

Registration methods take two inputs: `input` is the fixed reference, `moving`
is the one that gets transformed. They write the estimated transform next to
the output as `<output>.json` (`obj.transform`).

`pl.catalog().describe("simpleitk_registration.rigid")` prints every parameter.
The theory behind each module (with the formulas) is in the catalog too:
`pl.catalog().module("sdf").theory`.

## Examples

**Clean a LiDAR sweep and cluster the objects**

```python
sweep = pl.load("sweep.las")
objects = sweep.run("ground_removal").run("object_clustering", eps=0.7, min_points=10)
objects.to_open3d()
```

**Register two CT volumes and check the result**

```python
ct_day0 = pl.load("day0.nii")
ct_day7 = pl.load("day7.nii")
reg = ct_day0.register(ct_day7, metric="mattes_mutual_information", num_iterations=300)
print(reg.transform["rotation_deg"], reg.transform["translation_mm"])
diff = ct_day0.run("difference_analysis", moving=reg)
```

**Mesh from a scan, then simplify for the web**

```python
mesh = pl.load("scan.ply").poisson(depth=10).decimate(target_reduction=0.8)
mesh.save("web/scan.ply")
```

**Follow a long run**

```python
res = pl.run(
    "simpleitk_registration",
    "bspline",
    "a.mha",
    moving="b.mha",
    on_progress=lambda pct: print(f"{pct}%"),
    on_log=print,
    timeout=1800,
)
```

## Cloud (optional)

The hosted platform adds sharing, GPU methods (image → 3D, 2D AI), browser
viewers and a node editor. The 0.1.x client is unchanged, under `pardesline.cloud`
and at the top level:

```python
pl.login()  # email + one-time code
remote = pl.upload(surface)  # an Object or a path
pl.share(remote, to="colleague@lab.org")
remote.view()  # link to the 3D viewer
```

## Roadmap

- **Datasets**: `pl.load("hf://org/name")`, `pl.load("sample://rire_ct_mr")`,
  `pl.load("/my/folder")` with a manifest that carries licence, roles, frame
  and units; `pl.scan` to draft one for a private folder.
- **Object model**: frames, units, labels and provenance on every object;
  `to_mesh()`, `align()`, `segment()` with the same names everywhere.
- **Local MCP server**: `pardesline mcp` exposes the catalog to AI coding
  agents without an account.
- Learned models (segmentation, registration) behind the same function names.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports with the command, the log
and your library versions are the most useful thing you can send.

## Licence

Apache License 2.0. Open3D, PyVista, VTK, SimpleITK, NumPy and the other
dependencies keep their own licences (see [NOTICE](NOTICE)).

## Citation

```bibtex
@software{pardesline,
  author = {Tabet, Jonathan},
  title  = {PardesLine: 3D vision and medical imaging in one Python package},
  year   = {2026},
  url    = {https://github.com/pardesline/pardesline}
}
```
