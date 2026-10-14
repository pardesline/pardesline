# The catalog: 73 algorithms

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

# What `pardesline` gives you, call by call

| | |
|---|---|
| **`pl.load(path)`** | A local file as a typed `Object`: `PointCloud`, `Mesh`, `Volume`, `LabelMap`, `Transform`, `Image`. Volumes get their frame (LPS, mm, affine) from the header; glTF is Y-up metres by specification; formats that carry no unit stay *unknown* until you say. |
| **`pl.load(dataset)`** | A `Dataset` from one of the 43 bundled manifests (`pardesline datasets`), from `hf://org/name[/folder]`, `s3://bucket/prefix`, `tcia://Collection`, from your own manifest file, or from a folder via `pl.scan`. Files are fetched on first access (per file from the Hub or a bucket, member by member out of remote archives, series by series from TCIA, SHA-512-verified downloads), cached. |
| **`pl.load("sweep.bin", layout=...)`** | A raw `.npy` / `.npz` / `.bin` array as a `PointCloud` or a grid, through a declared layout (dtype, shape, columns, key). Never guessed; materialised once as PLY / MetaImage so every algorithm runs on it. |
| **`ds.export(folder)`** | A standard copy of any dataset: PLY / MetaImage / NIfTI files, one `.pardesline.json` sidecar each (frame, units, labels, licence, provenance) and a local manifest. |
| **`obj.run("module.method", **params)`** | Any algorithm; the result is a new `Object` that keeps the frame and licence and records the step. Aliases: `downsample`, `remove_outliers`, `normals`, `poisson`, `ball_pivoting`, `decimate`, `smooth`, `to_points`, `icp`, `ransac`, `register`, `segment`. |
| **Conversions named after the job** | `Volume.segment()` -> `LabelMap`; `LabelMap.to_mesh(label)` exact boundary in world coordinates; `Volume.to_mesh(isovalue)`; `Mesh.to_points()`; `PointCloud.to_mesh()` (Poisson, lossy); `PointCloud.align(moving)`, `Volume.align(moving)`; `clean()`. |
| **`pl.run(module, method, input, **params)`** | The same without the object wrapper. Returns output path, sidecar JSON, log and timing. |
| **`pl.catalog()`** | Every module, method and parameter with type, default, range, choices and description. `pl.describe("point_cloud_reconstruction.poisson")`. |
| **`obj.to_open3d()` / `to_pyvista()` / `to_sitk()` / `to_numpy()`** | Hand the result to the library you already use. `pl.o3d`, `pl.pv`, `pl.sitk` are the real libraries when installed. |
| **`pardesline` CLI** | `pardesline list`, `pardesline describe ...`, `pardesline run module.method in.ply -o out.ply --voxel_size 0.02`, `pardesline datasets`, `pardesline fetch amos22 --take 2`, `pardesline export msd_task02_heart ./heart --take 2`. |
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

# Examples

**Clean a LiDAR sweep and cluster the objects**

```python
sweep = pl.load("sweep.las").with_frame("sensor", "m")
objects = sweep.run("ground_removal").run("object_clustering", eps=0.7, min_points=10)
objects.to_open3d()
```

**Register two CT volumes and check the result**

```python
ct_day0 = pl.load("day0.nii")  # LPS, mm, affine from the header
ct_day7 = pl.load("day7.nii")
reg = ct_day0.align(ct_day7, metric="mattes_mutual_information", num_iterations=300)
print(reg.transform["rotation_deg"], reg.transform["translation_mm"])
diff = ct_day0.run("difference_analysis", moving=reg)
```

**Segmentation to a printable surface**

```python
mask = pl.load("ct.mha").segment(lower=200, upper=600)
bone = mask.to_mesh(label=1).decimate(target_reduction=0.8)
bone.save("bone.stl")  # + bone.stl.pardesline.json: LPS mm, licence, every step
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
