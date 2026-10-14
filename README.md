# PardesLine

[![PyPI](https://img.shields.io/pypi/v/pardesline.svg)](https://pypi.org/project/pardesline/)
[![Python](https://img.shields.io/pypi/pyversions/pardesline.svg)](https://pypi.org/project/pardesline/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![CI](https://github.com/pardesline/pardesline/actions/workflows/ci.yml/badge.svg)](https://github.com/pardesline/pardesline/actions/workflows/ci.yml)

**3D vision and medical imaging in one Python package.** 73 algorithms on point
clouds, meshes and volumes, with a typed catalog of 371 parameters, that run on
your machine with `pip install pardesline` — the same code that powers the
[PardesLine platform](https://appbeta.pardesline.com).

```python
import pardesline as pl

scan = pl.load("scan.ply")  # a local point cloud
surface = scan.downsample(voxel_size=0.01).remove_outliers().normals().poisson(depth=9)
surface.save("surface.ply")  # + surface.ply.pardesline.json (frame, licence, provenance)

ds = pl.load("msd_task02_heart")  # 30 cardiac MRIs, read case by case out of the MSD tar (HTTP Range)
s = ds.filter(split="Tr")[0]  # roles: mri, mask
atrium = s.mask.to_mesh(label=1)  # exact left-atrium surface, LPS millimetres, licence attached

ds = pl.load("hf://farrell236/NSCLC-Radiomics-NIFTI")  # a Hugging Face repo: 422 lung CTs + masks
ds["LUNG1-001"].mask.labels  # {1: 'esophagus', 2: 'gtv', 3: 'heart', ...}

ct = pl.load("tcia://Pancreas-CT")[0].ct  # a TCIA collection: DICOM series fetched on access
liver = pl.load("totalsegmentator_ct")[0].liver.to_mesh()  # one of 117 organ masks, 1 228 CTs
t1 = pl.load("s3://openneuro.org/ds000228")[0].t1w  # any OpenNeuro dataset from its public bucket

sweep = pl.load("kitti_raw_2011_09_26_drive_0001")[0].lidar  # a KITTI .bin read through its layout
sweep.run("ground_removal").run("object_clustering", eps=0.7, min_points=10)

ds = pl.load("/data/study_A", license="internal", units={"mesh": "mm"})  # your own folder
ds.export("/data/study_A_standard")  # standard files + sidecars + manifest
```

> **Status: 0.2.0 alpha.** Local execution of the 73 algorithms, the typed
> catalog, the object model (frames, units, labels, licence, provenance),
> 43 bundled dataset manifests (35 medical: DICOM, NIfTI, MetaImage, npz,
> STL meshes, Gaussian splats), `pl.load` for any Hugging Face repo, public
> S3 bucket or TCIA collection with the same questions as a private folder,
> raw-array layouts and `pl.scan` are in and tested on Linux, Windows and macOS. Next: splats as a first-class
> kind, learned models, the local MCP server. See [Roadmap](#roadmap).

## Install

```bash
pip install "pardesline[all]"        # everything: Open3D, PyVista, SimpleITK, huggingface_hub
pip install "pardesline[local]"      # point clouds, meshes, SDF, LiDAR (Open3D, PyVista)
pip install "pardesline[medical]"    # volumes, DICOM, registration, segmentation (SimpleITK)
pip install "pardesline[hf]"         # datasets hosted on the Hugging Face Hub
pip install pardesline               # catalog, object model, manifests and cloud client only
```

Python 3.10 – 3.12 for the native extras (Open3D 0.19 has no 3.13 wheels);
the core package also runs on 3.13.

## What you get

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
come from (with checksums or a Hub revision), under which licence, how files
group into samples, and what each file cannot say by itself (frame, units,
label meanings, array layout). Forty-three manifests ship with the package;
`pl.datasets()` / `pardesline datasets` list them, `pl.describe(name)` prints
one. Every public source below was listed and one file fetched from it on
2026-10-13/14; the licence column is what the source states.

**Medical volumes: CT, MRI, PET, ultrasound (NIfTI, MetaImage, npz)**

| Dataset | What | Source | Licence |
|---|---|---|---|
| `msd_task01_braintumour` ... `msd_task10_colon` | the ten Medical Segmentation Decathlon tasks (2 633 CT/MRI with labels: brain tumour, heart, liver, hippocampus, prostate, lung, pancreas, hepatic vessels, spleen, colon) | one tar per task on S3, read by Range | CC-BY-SA-4.0 |
| `amos22` | 600 abdominal CT/MRI, 15 organs | zip64 on Zenodo, read by Range (24 GB) | CC-BY-SA-4.0 |
| `totalsegmentator_ct` | 1 228 CTs, 117 structures as one mask role each (`s.liver`, `s.vertebrae_l3`...) | zip on Zenodo, read by Range (24 GB) | CC-BY-4.0 |
| `totalsegmentator_mri` | 298 MRIs, 56 structures | zip on Zenodo, read by Range | CC-BY-NC-SA-2.0 |
| `luna16` | 888 thorax CTs for nodule detection (MetaImage + raw) | ten zips on Zenodo, read by Range | CC-BY-4.0 |
| `ixi_brain_mri` | ~600 healthy brains, T1 / T2 / PD / MRA | four tars at Imperial College, read by Range | CC-BY-SA-3.0 |
| `verse19_spine` | 160 spine CTs, 28-class vertebra masks, centroids | three zips on S3, read by Range | CC-BY-SA-4.0 |
| `spider_lumbar_mri` | 447 lumbar MRIs, vertebra / disc / canal masks | two zips on Zenodo, read by Range | CC-BY-4.0 |
| `hf_openmind` | OpenMind head MRI, one OpenNeuro study at a time (114k images in all) | `hf://MIC-DKFZ/OpenMind` | CC-BY-4.0 |
| `hf_nsclc_radiomics` | 422 lung CTs with tumour and organ masks (TCIA, NIfTI) | `hf://farrell236/NSCLC-Radiomics-NIFTI` | CC-BY-3.0 |
| `hf_kits23` | 489 kidney-tumour CTs, kidney / tumour / cyst | `hf://neheller/KiTS-Challenge-Imaging` | CC-BY-NC-SA-4.0 |
| `hf_abdomenatlas_mini` | abdominal CTs with nine organ masks (first 100 of 5 195) | `hf://AbdomenAtlas/AbdomenAtlas1.0Mini`, gated | CC-BY-NC-SA-4.0 |
| `hf_ct_rate_valid` | chest CTs paired with radiology reports (first 20 of 50 188) | `hf://ibrahimhamamci/CT-RATE`, gated | CC-BY-NC-SA-4.0 |
| `hf_biomedsegfm_3d_val` | 2 144 CT / MRI / PET / 3-D ultrasound / microscopy volumes as npz | `hf://junma/CVPR-BiomedSegFM` | CC-BY-NC-SA-4.0 |
| `openneuro_ds000228` | T1w MRI of 155 children and adults; any OpenNeuro dataset via `s3://openneuro.org/dsXXXXXX` | public S3 bucket | PDDL / CC0 |
| `rire_brain`, `popi_lung_4dct`, `liver_tumor_patient01`, `visible_human_head_mri` | the SimpleITK notebook excerpts | https + SHA-512 | research use, terms to confirm |

**DICOM series**

| Dataset | What | Source | Licence |
|---|---|---|---|
| `tcia_pancreas_ct` | 82 abdominal CTs (NIH) | TCIA, NBIA API | CC-BY-3.0 |
| `tcia_lidc_idri` | 1 018 thorax CTs + DICOM SEG | TCIA, NBIA API | CC-BY-3.0 |
| `tcia_nsclc_radiomics_dicom` | 422 planning CTs + RTSTRUCT + SEG | TCIA, NBIA API | CC-BY-3.0 |
| `tcia_prostate_3t` | 64 T2 prostate MRIs | TCIA, NBIA API | CC-BY-3.0 |
| `chaos_abdomen` | 20 CT + 20 MR (T1 in/out-phase, T2 SPIR) as DICOM series | zip on Zenodo, read by Range | CC-BY-NC-SA-4.0 |

Any of the 156 public TCIA collections: `pl.load("tcia://Collection[/CT,MR]")`.

**Anatomical meshes, splats and point clouds**

| Dataset | What | Source | Licence |
|---|---|---|---|
| `medshapenet` | 106 101 anatomical and instrument shapes as STL (`ds.filter(structure="liver")`) | public URL index | CC-BY-4.0, per source |
| `c3vd_endoscopy_splats` | ten colonoscopy scenes as Gaussian splats + point clouds | zip on Zenodo, read by Range | CC-BY-4.0 (C3VD NC) |
| `hf_3d_arena` | 29 image-to-3D generators x 100 images, meshes and splats | `hf://3d-arena/3d-arena` | MIT |
| `hf_objaverse_glb_shard` | 5 000 glTF objects (one shard) | `hf://allenai/objaverse` | ODC-By, per-object CC |
| `open3d_bunny`, `open3d_armadillo`, `open3d_icp_demo` | Open3D demo data | `open3d.data` | terms to confirm |

**Driving and LiDAR**

| Dataset | What | Source | Licence |
|---|---|---|---|
| `kitti_raw_2011_09_26_drive_0001` | 108 Velodyne sweeps + stereo images | zip on S3, read by Range | CC-BY-NC-SA-3.0 |
| `hf_kitti360_gs_subset` | 16 KITTI-360 chunks: points + Gaussian-splat arrays | `hf://GaussianWorld/...` | CC-BY-NC-SA-3.0 |
| `hf_uniocc_carla_mini` | LiDAR, cameras and occupancy grids (CARLA) | `hf://tasl-lab/uniocc` | MIT |

Access is lazy by design. Indexing the MSD heart tar costs 32 KB (61
headers), the KITTI zip 157 KB, the 24 GB AMOS zip64 145 KB and the 145k-entry
TotalSegmentator zip 14 MB; a case then costs its own size. Hub manifests scope
their listing to the folders they need and a listing is capped at 20 000
files: listing OpenMind whole (266 721 files) takes 15 minutes and is
rate-limited for anonymous clients. Gated repositories (AbdomenAtlas, CT-RATE)
need your own Hub token after you accept their terms; restricted TCIA
collections answer 401 and are left to the NBIA Data Retriever. The package
never scripts past a click-through.

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

**Any Hugging Face repo, public bucket or TCIA collection.**
`pl.load("hf://org/name/sub/folder")`, `pl.load("s3://bucket/prefix")` and
`pl.load("tcia://Collection/CT")` use the bundled manifest when there is one,
otherwise list the source, draft a manifest and ask the same questions
(licence from the Hub card or the archive's policy, units, labels, and the
layout of raw arrays). When nothing is left to ask, the dataset loads directly:

```python
pl.load("hf://acme/scans/raw")
# NeedsConfirmation: hf_acme_scans: 1 question(s) ...
#   - roles.scan.layout: raw/p01/scan.bin is a raw array. What is in it? ...
ds = pl.load(
    "hf://acme/scans/raw",
    types={"scan": "points"},
    layout={"scan": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},
    units={"scan": "m"},
    frame={"scan": "sensor"},
)
```

Sources: `local` folders; `https` files with SHA-512 or md5 (and tar/zip
downloads); `hf` repos through `huggingface_hub` (`pip install
"pardesline[hf]"`, your own token for gated data and for higher rate limits);
`archive`: one or several remote zips or tars read member by member with HTTP
Range requests (zip64 included, index cached; one verified download when the
server ignores ranges); `s3`: a public bucket listed anonymously; `tcia`: a
collection of The Cancer Imaging Archive through the NBIA API, one DICOM
series per entry; `urllist`: a text index with one download URL per line;
Open3D demo data. A DICOM series is a folder entry: fetching it brings every
file; a MetaImage header brings its `.raw`.

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

- **More manifests**: BraTS (Synapse DUA), ShapeNetCore (gated), the
  nuScenes-derived UniOcc splits, VerSe 2020, the remaining TCIA CT/MR
  collections as a generated set; a PardesLine org on the Hub mirroring the
  permissive ones.
- **Splats** (`.splat`, `.spz`, glTF Gaussian-splat extension, the KITTI-360
  array sets) as a first-class kind with its own conversions.
- **Local MCP server**: `pardesline mcp` exposes the catalog and datasets to
  AI coding agents without an account.
- Learned models (segmentation, registration) behind the same function names.

## For AI coding agents

The `skills/` folder holds eight Claude Code skills, grounded in the code and
checked by the test suite (every module, method, parameter and dataset they
mention must exist): `using-pardesline` (start here), `catalog-and-run`,
`object-model`, `datasets-and-manifests`, `scanning-private-folders`,
`medical-volumes`, `cloud-client`, `contributing-algorithms`. Install them as
a plugin:

```
/plugin marketplace add pardesline/pardesline
/plugin install pardesline@pardesline
```

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
