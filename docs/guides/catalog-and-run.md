---
title: "The catalog and pl.run"
description: "Run any of pardesline's 73 catalogued algorithms locally with `pl.run(module, method, input, **params)` or the `pardesline run` CLI, and read the typed cat"
---

# The catalog and pl.run

# The catalog and `pl.run`

## Module and method ids (all 73)

| Module | Methods | Input formats |
|---|---|---|
| `point_cloud_processing` | voxel_downsample, statistical_outlier_removal, radius_outlier_removal, mesh_to_pointcloud | .ply .pcd .txt .xyz |
| `mesh_processing` | subdivision, simplification, mesh_to_pcd_uniform, mesh_to_pcd_poisson_disk | .ply .obj .stl .off |
| `voxel_to_mesh` | voxelization, binary_erosion | .ply .obj .stl .off |
| `sdf` | compute_sdf, occupancy_reconstruction, sdf_voxel_visualization | .ply .obj .stl .off |
| `point_cloud_reconstruction` | poisson, convex_hull, alpha_shape, ball_pivoting | .ply .pcd .txt .xyz |
| `registration` (two inputs) | ransac_global, icp_refinement, ransac_icp_pipeline | .ply .pcd .txt .xyz |
| `deformable_registration` | cpd_deformable (two inputs), gaussian_deformation | .ply .pcd .txt .xyz |
| `point_cloud_segmentation` | ransac_plane, dbscan_clustering | .ply .pcd .txt .xyz |
| `stereo_3d_reconstruction` | depth_colorization, depth_filter | .ply .pcd .txt .xyz |
| `lidar_scene_detection` | height_colorization, ground_removal, object_clustering | .ply .pcd .txt .xyz .las |
| `lidar_camera_fusion` | intensity_colorization, roi_extraction, multi_resolution | .ply .pcd .txt .xyz .las |
| `features_extraction` | normal_estimation, fpfh_features, curvature_estimation | .ply .pcd .txt .xyz |
| `collision_detection` | sdf_collision, penetration_depth | .ply .obj .stl .off |
| `pyvista_mesh_processing` | pv_decimate, pv_subdivide, pv_smooth_laplacian, pv_smooth_taubin, pv_clean, pv_fill_holes, pv_compute_normals, pv_triangulate, pv_extract_surface | .ply .obj .stl .vtk .vtu |
| `pyvista_pointcloud_processing` | pv_threshold, pv_clip_plane, pv_clip_box, pv_random_sample, pv_extract_points | .ply .pcd .vtk .vtu .obj .stl |
| `pyvista_volume_processing` | pv_contour, pv_slice, pv_slice_orthogonal, pv_threshold_volume, pv_extract_geometry, pv_extract_cells | .vti .vtk .vtu .ply .obj .stl |
| `pyvista_analysis` | pv_curvature, pv_distance, pv_glyph, pv_vector_magnitude, pv_scalar_stats, pv_extract_feature_edges | .ply .obj .stl .vtk .vtu |
| `simpleitk_registration` (two inputs) | rigid, advanced_rigid, affine, bspline, demons, difference_analysis | .vti .mha .nrrd .nii .dcm |
| `simpleitk_segmentation` | otsu_threshold, manual_threshold, connected_components, watershed | .vti .mha .nrrd .nii |

Outputs are `.ply` for the first 17 modules and `.vti` for the SimpleITK ones.
Registration methods also write `<output>.json` next to the output with the
estimated transform (`rotation_deg`, `translation_mm`, matrices).

Do not guess parameter names: print them.

```python
print(pl.describe("point_cloud_reconstruction.poisson"))
# point_cloud_reconstruction.poisson  -  Poisson Surface Reconstruction
#   output: .ply
#   parameters:
#     depth: int = 9 [4..12]
#       Octree depth ...
#     density_quantile: float = 0.01 [0.0..0.5]
#     ...
m = pl.catalog().method("simpleitk_registration", "rigid")
[p.name for p in m.parameters]  # learning_rate, num_iterations, sampling_percentage, initializer, metric, ...
m.dual_input  # True
pl.catalog().methods_for(".mha")  # every Method accepting .mha
pl.catalog().find("poisson", ".ply")  # resolve a bare id for a file type
```

A few parameters that come up constantly: `voxel_downsample(voxel_size)`,
`statistical_outlier_removal(nb_neighbors, std_ratio)`, `poisson(depth,
density_quantile, normal_radius)`, `pv_decimate(target_reduction)`,
`pv_smooth_laplacian(n_iterations)`, `mesh_to_pcd_poisson_disk(num_points)`,
`icp_refinement(voxel_size, max_iterations >= 100, icp_estimation_method)`,
`ransac_icp_pipeline(voxel_size, rotation_degrees)`,
`dbscan_clustering(eps, min_points)`, `rigid(num_iterations, metric,
initializer=GEOMETRY|MOMENTS, sampling_percentage, shrink_factors="4,2,1")`,
`manual_threshold(lower, upper)`, `connected_components(min_size)`.

## `pl.run`

```python
res = pl.run("simpleitk_registration", "rigid", "ct.mha", moving="mr.mha", num_iterations=200)
res = pl.run("point_cloud_processing.voxel_downsample", "scan.ply", "small.ply", voxel_size=0.02)
res.output      # Path written (default: pl.output_dir()/<stem>_<method>_<id>.<ext>)
res.sidecar     # Path of <output>.json when the script wrote one (registration), else None
res.log         # full stdout+stderr of the script, ANSI stripped
res.duration_s, res.command, res.params (as sent), res.provenance()
```

Signature: `run(module, method=None, input=None, /, output=None, *, moving=None,
params=None, timeout=600, python=None, on_log=None, on_progress=None, cwd=None,
**params)`. The first three are positional-only, so a parameter literally
called `method` or `input` (e.g. `pv_contour(method="flying_edges")`) still
works as a keyword. `params={...}` and keywords may be mixed but not repeat.

Validation before execution (raises `pl.ParameterError`): unknown name (with a
"did you mean"), wrong type, out of `[min..max]`, enum not in `options`
(case-insensitive, normalised), `output` extension not the method's, input
extension not accepted by the module, `moving` missing for a two-input method
or given to a single-input one. Coercion to the command line: floats `repr`,
bools `true`/`false`, lists joined with commas (`shrink_factors=[4, 2, 1]`).

Execution: a subprocess `python -m pardesline.ops.<module>.<script> --input ...
--output ... [--moving ...] --name value ...` with `PYTHONUNBUFFERED=1`,
`MPLBACKEND=Agg`, `PYVISTA_OFF_SCREEN=true`, `LOGURU_COLORIZE=False`. Lines
starting with `PROGRESS:NN` go to `on_progress(int)`; every other line goes to
`on_log(str)` or to loguru at DEBUG. `timeout` kills the child and raises
`pl.RunError` (`.returncode is None`); a non-zero exit raises `pl.RunError`
with the last 25 log lines in `str(err)`; exit 0 without an output file is
also a `RunError`.

## CLI

```bash
pardesline list [--ext .mha] [--category registration]
pardesline describe simpleitk_registration.rigid
pardesline run point_cloud_processing.voxel_downsample scan.ply -o small.ply --voxel_size 0.02
pardesline run simpleitk_registration.rigid ct.mha --moving mr.mha -o reg.vti --num_iterations 200 -q
pardesline version
```

Parameters after the input are `--name value` (booleans `--flag true`). The
run prints the output path (and the sidecar path) on stdout and echoes the
script log on stderr unless `-q`. Exit code 1 with `error: ...` on any
`PardesLineError` or missing file. The cloud commands (`login`, `upload`,
`send`, `inbox`, `ls`, `download`, `share`, `whoami`, `logout`) are forwarded
to the cloud client.

## Running a script directly (same contract as the hosted platform)

```bash
python -m pardesline.ops.simpleitk_segmentation.otsu_threshold --input ct.mha --output mask.vti
python -m pardesline.ops.registration.icp_refinement --input fixed.ply --output moved.ply --moving moving.ply --voxel_size 0.05
```

Exit 0 means the output was written. Prefer `pl.run` from Python: it
validates, names the output and captures the log.

<sub>Source: `skills/catalog-and-run/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-16.</sub>
