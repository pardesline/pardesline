# PardesLine

**3D vision and medical imaging in one Python package.** 73 algorithms on point
clouds, meshes and volumes, with a typed catalog of 371 parameters, that run on
your machine with `pip install pardesline` — the same code that powers the
[PardesLine platform](https://appbeta.pardesline.com).

```python
import pardesline as pl

scan = pl.load("scan.ply")  # a local point cloud
surface = scan.downsample(voxel_size=0.01).remove_outliers().normals().poisson(depth=9)
surface.save("surface.ply")  # + surface.ply.pardesline.json (frame, licence, provenance)

ds = pl.load("rire_brain")  # a dataset: manifest + files fetched on first access
s = ds[0]  # roles: ct, mr_t1
moved = s.ct.align(s.mr_t1)  # rigid CT/MR registration, transform in moved.transform

mask = s.ct.segment(lower=200, upper=600)  # LabelMap, label 1
bone = mask.to_mesh(label=1)  # exact surface, in LPS millimetres

ds = pl.load("/data/study_A", license="internal", units={"mesh": "mm"})  # your own folder
```

> **Status: 0.2.0 alpha.** Local execution of the 73 algorithms, the typed
> catalog, the object model (frames, units, labels, licence, provenance),
> dataset manifests with seven bundled datasets and `pl.scan` for private
> folders are in and tested on Linux, Windows and macOS. Next: more public
> manifests (`hf://`), learned models, the local MCP server. See [Roadmap](#roadmap).

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
| **`pl.load(path)`** | A local file as a typed `Object`: `PointCloud`, `Mesh`, `Volume`, `LabelMap`, `Transform`, `Image`. Volumes get their frame (LPS, mm, affine) from the header; glTF is Y-up metres by specification; formats that carry no unit stay *unknown* until you say. |
| **`pl.load(dataset)`** | A `Dataset` from a bundled manifest (`rire_brain`, `popi_lung_4dct`, `liver_tumor_patient01`, `visible_human_head_mri`, `open3d_bunny`, `open3d_armadillo`, `open3d_icp_demo`), from your own manifest file, or from a folder via `pl.scan`. Files are fetched on first access, verified by SHA-512, cached. |
| **`obj.run("module.method", **params)`** | Any algorithm; the result is a new `Object` that keeps the frame and licence and records the step. Aliases: `downsample`, `remove_outliers`, `normals`, `poisson`, `ball_pivoting`, `decimate`, `smooth`, `to_points`, `icp`, `ransac`, `register`, `segment`. |
| **Conversions named after the job** | `Volume.segment()` -> `LabelMap`; `LabelMap.to_mesh(label)` exact boundary in world coordinates; `Volume.to_mesh(isovalue)`; `Mesh.to_points()`; `PointCloud.to_mesh()` (Poisson, lossy); `PointCloud.align(moving)`, `Volume.align(moving)`; `clean()`. |
| **`pl.run(module, method, input, **params)`** | The same without the object wrapper. Returns output path, sidecar JSON, log and timing. |
| **`pl.catalog()`** | Every module, method and parameter with type, default, range, choices and description. `pl.describe("point_cloud_reconstruction.poisson")`. |
| **`obj.to_open3d()` / `to_pyvista()` / `to_sitk()` / `to_numpy()`** | Hand the result to the library you already use. `pl.o3d`, `pl.pv`, `pl.sitk` are the real libraries when installed. |
| **`pardesline` CLI** | `pardesline list`, `pardesline describe ...`, `pardesline run module.method in.ply -o out.ply --voxel_size 0.02`. |
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

## Datasets and manifests

`pl.load` never knows a dataset; it knows a **manifest**: where the files
come from (with checksums), under which licence, how files group into
samples, and what each file cannot say by itself (frame, units, label
meanings, array layout). Seven manifests ship with the package; `pl.datasets()`
lists them, `pl.describe("popi_lung_4dct")` prints one.

```python
ds = pl.load("popi_lung_4dct")  # six breathing phases of one thorax CT + a mask
ds.describe()  # licence, citation, roles, samples
phase0 = ds["phase_00"]
phase0.mask.labels  # {1: 'body', 2: 'lungs'}
lungs = phase0.mask.to_mesh(label=2)  # exact surface, LPS mm
moved = phase0.ct.align(ds["phase_50"].ct)

train, test = ds.split(by="patient", fractions=(0.8, 0.2), seed=0)  # leakage-free
```

**Your own folder.** `pl.scan` drafts a manifest (samples, roles, what the
headers say) and lists the questions it will not answer for you:

```python
pl.load("/data/study_A")
# NeedsConfirmation: study_a: 4 question(s) before this folder can be loaded:
#   - license: Who owns this data and under which terms may it be used?
#   - roles.mesh.units: p01/la.stl: the format carries no unit. mm, m, ...?
#   - roles.mask.labels: p01/seg.nii.gz looks like a label map. What does each value mean?
#   ...
# Draft saved: /data/study_A/pardesline.manifest.json

ds = pl.load(
    "/data/study_A",
    license="internal, no redistribution",
    units={"mesh": "mm"},
    labels={"mask": {1: "left_atrium"}},
)
```

Or edit the saved draft, or `interactive=True` to answer in the terminal, or
`assume=True` to proceed with unknowns (and warnings). Licence terms of
public datasets that could not be confirmed are marked `TO CONFIRM` in the
manifest and in `ds.license.describe()`.

Sources: `local` folders, `https` files with SHA-512 (and tar/zip archives),
`hf://` repos through `huggingface_hub` (`pip install "pardesline[hf]"`, your
own token for gated data), and Open3D demo data.

## Examples

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

- **More manifests**: the public 3D datasets people actually use (OpenMind,
  NSCLC-Radiomics, MSD, AMOS, Objaverse subsets, KITTI...), with licence tiers:
  permissive -> mirrored, non-commercial -> loader only, gated -> your own token.
- **Splats** (`.splat`, `.spz`, glTF Gaussian-splat extension) as a first-class kind.
- **Local MCP server**: `pardesline mcp` exposes the catalog and datasets to
  AI coding agents without an account.
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
