<p align="center">
  <a href="https://pardesline.github.io/pardesline/"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/docs/assets/logo.svg" width="360" alt="pardesline logo: wordmark with a point-cloud glyph"></a>
</p>

<h1 align="center">pardesline: 3D computer vision and medical imaging datasets, algorithms and models for Python</h1>

<p align="center"><b>Load 43 public 3D and medical datasets in one line, run 73 algorithms on point clouds, meshes and CT/MRI volumes with defaults that hold on real scans, hand the result to Open3D, PyVista or SimpleITK, or to an AI agent through MCP.</b></p>

<p align="center">
<a href="https://pypi.org/project/pardesline/"><img src="https://img.shields.io/pypi/v/pardesline.svg" alt="PyPI version"></a>
<a href="https://pypi.org/project/pardesline/"><img src="https://img.shields.io/pypi/pyversions/pardesline.svg" alt="Python versions"></a>
<a href="https://pepy.tech/projects/pardesline"><img src="https://static.pepy.tech/badge/pardesline/month" alt="PyPI downloads per month"></a>
<a href="https://github.com/pardesline/pardesline/actions/workflows/ci.yml"><img src="https://github.com/pardesline/pardesline/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
<a href="https://pardesline.github.io/pardesline/"><img src="https://img.shields.io/badge/docs-pardesline.github.io-f0a05a.svg" alt="Documentation"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License Apache-2.0"></a>
<a href="CITATION.cff"><img src="https://img.shields.io/badge/cite-CITATION.cff-lightgrey.svg" alt="Citation file"></a>
<a href="https://github.com/pardesline/pardesline/discussions"><img src="https://img.shields.io/badge/GitHub-Discussions-5aa0f0.svg" alt="GitHub Discussions"></a>
</p>

<p align="center">
  <a href="docs/showcase/README.md"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/docs/showcase/posters.gif" width="560" alt="Animated carousel of ten 3D vision and medical imaging pipelines built with pardesline: JEPA, DINOv3, ultrasound atlas transfer, Gaussian splats, 3D representations, atlas segmentation, PointNet, VAE anomaly detection, CT/MR registration, RANSAC + ICP"></a><br>
  <sub>Ten pipelines, one package: <a href="docs/showcase/README.md">the showcase</a> has the snippet, the expert skill and the MCP tool for each.</sub>
</p>

## 30-second demo: dataset in, registration out

```bash
pip install "pardesline[all]"
```

```python
import pardesline as pl
import pyvista as pv

s = pl.load("rire_brain")[0]  # CT + MR T1 of one head (19 MB); the licence line is printed, never guessed
moved = s.ct.align(s.mr_t1)  # rigid registration: SimpleITK, Mattes mutual information, catalog defaults
print(moved.transform["sub_transforms"][0]["rotation_deg"])  # [0.34, -0.35, -4.38] degrees

ct, mr = s.ct.to_pyvista(), moved.to_pyvista()  # the libraries you already use, one call away
p = pv.Plotter(shape=(1, 2))
p.subplot(0, 0)
p.add_mesh(ct.slice("z"), cmap="gray")
p.add_text("CT (fixed)")
p.subplot(0, 1)
p.add_mesh(ct.slice("z"), cmap="gray")
p.add_mesh(mr.slice("z"), cmap="magma", opacity=0.55)
p.add_text("MR T1 registered onto the CT")
p.show()
```

<p align="center"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/register_ct_mr_rire/rire_ct_mr.png" width="760" alt="Left: axial CT slice of the RIRE brain. Right: the same CT slice with the registered MR T1 overlaid in colour"></p>

Measured cold on a laptop: 7.6 s download, 8.8 s registration, 21.5 s total. The script is [examples/register_ct_mr_rire/run.py](examples/register_ct_mr_rire/run.py).

## Why this exists

- **Datasets are scattered and incompatible.** The Decathlon is a tar on S3, TCIA is a REST API that returns zips of DICOM, KiTS is on Hugging Face, KITTI is a zip of headerless binaries. pardesline describes each one in a manifest (files, roles, labels, frame, units, licence, citation) and fetches lazily, by HTTP Range inside archives when it can, so one sample costs one sample.
- **Nothing carries its meaning.** A `.bin` is numbers until someone says `(N, 4) float32, x y z reflectance, metres`. A NIfTI label map is integers until someone says `1 = anterior`. Manifests carry that; your own folders get it through `pl.scan`, which asks what it cannot know instead of guessing.
- **Open3D, PyVista and SimpleITK do not talk to each other.** One typed object (`PointCloud`, `Mesh`, `Volume`, `LabelMap`) converts between them, keeps frame, units, labels, licence and provenance, and exposes `to_open3d()`, `to_pyvista()`, `to_sitk()` when you want the library itself.
- **Textbook defaults break on real scans.** The ICP that converges on the tutorial fragments ends 32 degrees off on a noisy partial scan while reporting a 0.98 fitness. Every algorithm here runs behind one call with defaults tied to the data (voxel size from the bounding box, correspondence distances as multiples of it) and the sidecar records what was used. See [Defaults that work on real data](#defaults-that-work-on-real-data).
- **Models do not plug into datasets.** The expert skills and reference scripts (PointNet, DINOv3 features, JEPA, VAE, nnU-Net preparation) read any pardesline dataset. One-line access to pretrained models through the same manifest pattern is the next step on the [roadmap](#roadmap).

## Install

```bash
pip install pardesline                 # core: catalog, object model, datasets, CLI (no native libraries)
pip install "pardesline[local]"        # + Open3D, PyVista, SciPy, scikit-image: point clouds, meshes, LiDAR, SDF
pip install "pardesline[medical]"      # + SimpleITK: volumes, DICOM series, registration, segmentation
pip install "pardesline[hf]"           # + huggingface_hub: datasets on the Hub
pip install "pardesline[mcp]"          # + mcp: the local server for AI agents
pip install "pardesline[all]"          # everything above
```

| | Linux | macOS | Windows |
|---|---|---|---|
| Core (`pardesline`) | 3.10 – 3.13 | 3.10 – 3.13 | 3.10 – 3.13 |
| `[local]` / `[all]` | 3.10 – 3.13 | 3.10 – 3.13 (arm64) | 3.10 – 3.13 |

`[local]` needs Open3D wheels: 0.20 covers Python 3.10 – 3.13, 0.19 covers 3.10 – 3.12. pardesline 0.2.0 on PyPI pins Open3D below 0.20, so on Python 3.13 use 3.12 or install from `main` until 0.3.0 ships. Conda users: `conda create -n pl python=3.12 && pip install "pardesline[all]"` (Open3D and SimpleITK come from PyPI). Troubleshooting: [docs/running-modes.md](docs/running-modes.md).

## 📦 Datasets

One loader for every source. Files are fetched on access and verified; the licence and the citation travel with the data; `ds.describe()` says what each role is, in which frame and units, and what the labels mean.

```python
ds = pl.load("totalsegmentator_ct")  # 1 228 CTs, 117 structures, 23 GB zip on Zenodo: indexed with 14 MB
ct = ds.take(1)[0].ct  # one 50 MB volume fetched by HTTP Range, nothing else
ds = pl.load(
    "hf://neheller/KiTS-Challenge-Imaging"
)  # any Hugging Face repo: a manifest is drafted and confirmed
ds = pl.load("tcia://Pancreas-CT")  # any public TCIA collection: DICOM series as folders
ds = pl.scan("/data/my_study")  # your folder: drafts a manifest, asks for units / labels / licence
```

<!-- datasets-table:start (generated by docs/_gen/datasets_table.py; edit the manifests, not this table) -->
**Medical (35)**

| Dataset | Modality / type | Size | Licence | Source | One-line loader |
|---|---|---|---|---|---|
| [AMOS 22: abdominal multi-organ segmentation, 600 CT and MRI with 15 organ labels](https://pardesline.github.io/pardesline/datasets/amos22/) | CT / MRI / NIfTI (labels, volume) | 23.7 GB | CC-BY-SA-4.0 | zenodo.org | `pl.load("amos22")` |
| [C3VD colonoscopy scenes as Gaussian splats and point clouds (EndoGSLAM fits from PR-ENDO)](https://pardesline.github.io/pardesline/datasets/c3vd_endoscopy_splats/) | endoscopy / Gaussian splats / points (points, splat) | 7.7 GB | CC-BY-4.0 | zenodo.org | `pl.load("c3vd_endoscopy_splats")` |
| [CHAOS: abdominal CT and MR (T1 in/out-phase, T2 SPIR) as DICOM series, 40 patients](https://pardesline.github.io/pardesline/datasets/chaos_abdomen/) | CT / MRI / DICOM (volume) | 891 MB | CC-BY-NC-SA-4.0 | zenodo.org | `pl.load("chaos_abdomen")` |
| [AbdomenAtlas 1.0 Mini: abdominal CTs with nine organ masks (first 100 of 5 195 cases)](https://pardesline.github.io/pardesline/datasets/hf_abdomenatlas_mini/) | CT / NIfTI (labels, volume) | 7.8 GB | CC-BY-NC-SA-4.0 (gated) | Hugging Face `AbdomenAtlas/AbdomenAtlas1.0Mini` | `pl.load("hf_abdomenatlas_mini")` |
| [CVPR 2025 BiomedSegFM, 3-D validation set: 2 144 CT / MRI / PET / 3-D ultrasound / microscopy volumes as npz](https://pardesline.github.io/pardesline/datasets/hf_biomedsegfm_3d_val/) | CT / MRI / PET (labels, volume) | 19.5 GB | CC-BY-NC-SA-4.0 | Hugging Face `junma/CVPR-BiomedSegFM` | `pl.load("hf_biomedsegfm_3d_val")` |
| [CT-RATE: non-contrast chest CTs paired with radiology reports (first 20 validation cases)](https://pardesline.github.io/pardesline/datasets/hf_ct_rate_valid/) | CT / NIfTI (volume) | 6.8 GB | CC-BY-NC-SA-4.0 (gated) | Hugging Face `ibrahimhamamci/CT-RATE` | `pl.load("hf_ct_rate_valid")` |
| [KiTS23: 489 kidney-tumour CTs with kidney, tumour and cyst labels](https://pardesline.github.io/pardesline/datasets/hf_kits23/) | CT / NIfTI (labels, volume) | 87.9 GB | CC-BY-NC-SA-4.0 | Hugging Face `neheller/KiTS-Challenge-Imaging` | `pl.load("hf_kits23")` |
| [NSCLC-Radiomics (TCIA) as NIfTI: 422 lung-cancer CTs with organ and tumour segmentations](https://pardesline.github.io/pardesline/datasets/hf_nsclc_radiomics/) | CT / NIfTI (labels, volume) | 11.7 GB | CC-BY-3.0 | Hugging Face `farrell236/NSCLC-Radiomics-NIFTI` | `pl.load("hf_nsclc_radiomics")` |
| [OpenMind: head-and-neck 3D MRI pooled from OpenNeuro, one study at a time](https://pardesline.github.io/pardesline/datasets/hf_openmind/) | MRI / NIfTI (labels, volume) |  | CC-BY-4.0 | Hugging Face `MIC-DKFZ/OpenMind` | `pl.load("hf_openmind")` |
| [IXI: ~600 healthy-subject brain MRIs (T1, T2, PD, MRA) from three London hospitals](https://pardesline.github.io/pardesline/datasets/ixi_brain_mri/) | MRI / NIfTI (volume) | 24.6 GB | CC-BY-SA-3.0 | biomedic.doc.ic.ac.uk | `pl.load("ixi_brain_mri")` |
| [Liver tumour CT with three radiologists segmentations](https://pardesline.github.io/pardesline/datasets/liver_tumor_patient01/) | CT (labels, volume) | 2 MB | see source | https | `pl.load("liver_tumor_patient01")` |
| [LUNA16: 888 thoracic CTs (LIDC-IDRI subset) for lung nodule detection](https://pardesline.github.io/pardesline/datasets/luna16/) | CT / MetaImage (volume) | 64.8 GB | CC-BY-4.0 | zenodo.org | `pl.load("luna16")` |
| [MedShapeNet: 106 101 anatomical and surgical-instrument shapes as STL meshes](https://pardesline.github.io/pardesline/datasets/medshapenet/) | mesh / STL (mesh) | 1953.1 GB | CC-BY-4.0 | mml.ikim.nrw | `pl.load("medshapenet")` |
| [Medical Segmentation Decathlon, Task01 BrainTumour](https://pardesline.github.io/pardesline/datasets/msd_task01_braintumour/) | MRI / NIfTI (labels, volume) | 7.4 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task01_braintumour")` |
| [Medical Segmentation Decathlon, Task02 Heart: left-atrium segmentation on 30 cardiac MRIs](https://pardesline.github.io/pardesline/datasets/msd_task02_heart/) | MRI / NIfTI (labels, volume) | 456 MB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task02_heart")` |
| [Medical Segmentation Decathlon, Task03 Liver](https://pardesline.github.io/pardesline/datasets/msd_task03_liver/) | CT / NIfTI (labels, volume) | 28.2 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task03_liver")` |
| [Medical Segmentation Decathlon, Task04 Hippocampus](https://pardesline.github.io/pardesline/datasets/msd_task04_hippocampus/) | MRI / NIfTI (labels, volume) | 28 MB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task04_hippocampus")` |
| [Medical Segmentation Decathlon, Task05 Prostate](https://pardesline.github.io/pardesline/datasets/msd_task05_prostate/) | MRI / NIfTI (labels, volume) | 240 MB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task05_prostate")` |
| [Medical Segmentation Decathlon, Task06 Lung](https://pardesline.github.io/pardesline/datasets/msd_task06_lung/) | CT / NIfTI (labels, volume) | 8.9 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task06_lung")` |
| [Medical Segmentation Decathlon, Task07 Pancreas](https://pardesline.github.io/pardesline/datasets/msd_task07_pancreas/) | CT / NIfTI (labels, volume) | 12.0 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task07_pancreas")` |
| [Medical Segmentation Decathlon, Task08 HepaticVessel](https://pardesline.github.io/pardesline/datasets/msd_task08_hepaticvessel/) | CT / NIfTI (labels, volume) | 9.1 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task08_hepaticvessel")` |
| [Medical Segmentation Decathlon, Task09 Spleen](https://pardesline.github.io/pardesline/datasets/msd_task09_spleen/) | CT / NIfTI (labels, volume) | 1.6 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task09_spleen")` |
| [Medical Segmentation Decathlon, Task10 Colon](https://pardesline.github.io/pardesline/datasets/msd_task10_colon/) | CT / NIfTI (labels, volume) | 6.1 GB | CC-BY-SA-4.0 | msd-for-monai.s3-us-west-2.amazonaws.com | `pl.load("msd_task10_colon")` |
| [OpenNeuro ds000228: T1-weighted MRI of 155 children and adults (Richardson et al.)](https://pardesline.github.io/pardesline/datasets/openneuro_ds000228/) | MRI / NIfTI (volume) | 2.4 GB | PDDL-1.0 | S3 `openneuro.org` | `pl.load("openneuro_ds000228")` |
| [POPI-model: 4D-CT of one thorax, six breathing phases](https://pardesline.github.io/pardesline/datasets/popi_lung_4dct/) | CT / 4D (labels, volume) | 500 MB | see source | creatis.insa-lyon.fr | `pl.load("popi_lung_4dct")` |
| [RIRE training_001: CT and MR-T1 of one brain](https://pardesline.github.io/pardesline/datasets/rire_brain/) | CT / MRI (volume) | 19 MB | see source | rire.insight-journal.org | `pl.load("rire_brain")` |
| [SPIDER: lumbar spine MRI (T1, T2, T2 SPACE) of 218 patients with vertebra, disc and canal masks](https://pardesline.github.io/pardesline/datasets/spider_lumbar_mri/) | MRI / MetaImage (labels, volume) | 3.7 GB | CC-BY-4.0 | zenodo.org | `pl.load("spider_lumbar_mri")` |
| [TCIA LIDC-IDRI: 1 018 thoracic CTs for lung nodule analysis (DICOM)](https://pardesline.github.io/pardesline/datasets/tcia_lidc_idri/) | DICOM / CT (volume) | 122.1 GB | CC-BY-3.0 | TCIA `LIDC-IDRI` | `pl.load("tcia_lidc_idri")` |
| [TCIA NSCLC-Radiomics: 422 lung-cancer CTs with RTSTRUCT and SEG contours (DICOM)](https://pardesline.github.io/pardesline/datasets/tcia_nsclc_radiomics_dicom/) | DICOM / CT (volume) | 32.2 GB | CC-BY-3.0 | TCIA `NSCLC-Radiomics` | `pl.load("tcia_nsclc_radiomics_dicom")` |
| [TCIA Pancreas-CT: 82 abdominal contrast-enhanced CTs (NIH)](https://pardesline.github.io/pardesline/datasets/tcia_pancreas_ct/) | DICOM / CT (volume) | 8.8 GB | CC-BY-3.0 | TCIA `Pancreas-CT` | `pl.load("tcia_pancreas_ct")` |
| [TCIA Prostate-3T: 64 T2-weighted prostate MRIs (DICOM)](https://pardesline.github.io/pardesline/datasets/tcia_prostate_3t/) | DICOM / MRI (volume) | 200 MB | CC-BY-3.0 | TCIA `Prostate-3T` | `pl.load("tcia_prostate_3t")` |
| [TotalSegmentator CT dataset v2.0.1: 1 228 CT volumes with 117 anatomical structures](https://pardesline.github.io/pardesline/datasets/totalsegmentator_ct/) | CT / NIfTI (labels, volume) | 23.0 GB | CC-BY-4.0 | zenodo.org | `pl.load("totalsegmentator_ct")` |
| [TotalSegmentator MRI dataset v1.0.0: 298 MRI volumes with 56 anatomical structures](https://pardesline.github.io/pardesline/datasets/totalsegmentator_mri/) | MRI / NIfTI (labels, volume) | 2.3 GB | CC-BY-NC-SA-2.0 | zenodo.org | `pl.load("totalsegmentator_mri")` |
| [VerSe 2019: 160 spine CTs with vertebra-level label maps and centroids](https://pardesline.github.io/pardesline/datasets/verse19_spine/) | CT / NIfTI (labels, volume) | 12.0 GB | CC-BY-SA-4.0 | s3.bonescreen.de | `pl.load("verse19_spine")` |
| [Visible Human Project: MRI of the head](https://pardesline.github.io/pardesline/datasets/visible_human_head_mri/) | MRI (volume) | 2 MB | see source | nlm.nih.gov | `pl.load("visible_human_head_mri")` |

**General 3D (8)**

| Dataset | Modality / type | Size | Licence | Source | One-line loader |
|---|---|---|---|---|---|
| [3D Arena: image-to-3D outputs of 29 generators on 100 shared input images](https://pardesline.github.io/pardesline/datasets/hf_3d_arena/) | mesh / Gaussian splats (image, mesh, splat) | 19.5 GB | MIT | Hugging Face `3d-arena/3d-arena` | `pl.load("hf_3d_arena")` |
| [KITTI-360 street chunks as point clouds and Gaussian splats (GaussianWorld subset, 16 chunks)](https://pardesline.github.io/pardesline/datasets/hf_kitti360_gs_subset/) | LiDAR / points / Gaussian splats (points) | 2.4 GB | CC-BY-NC-SA-3.0 | Hugging Face `GaussianWorld/kitti_360_subset_chunk_gs_preprocessed` | `pl.load("hf_kitti360_gs_subset")` |
| [Objaverse 1.0, one shard of glTF meshes (5 000 objects)](https://pardesline.github.io/pardesline/datasets/hf_objaverse_glb_shard/) | mesh (mesh) | 14.6 GB | ODC-By-1.0 | Hugging Face `allenai/objaverse` | `pl.load("hf_objaverse_glb_shard")` |
| [UniOcc, CARLA 10 Hz mini split: LiDAR sweeps, camera views and semantic occupancy grids](https://pardesline.github.io/pardesline/datasets/hf_uniocc_carla_mini/) | LiDAR / points (image, labels, points) | 4.9 GB | MIT | Hugging Face `tasl-lab/uniocc` | `pl.load("hf_uniocc_carla_mini")` |
| [KITTI raw, drive 2011_09_26_0001: 108 Velodyne sweeps with the four camera streams](https://pardesline.github.io/pardesline/datasets/kitti_raw_2011_09_26_drive_0001/) | LiDAR / points / stereo (image, points) | 459 MB | CC-BY-NC-SA-3.0 | s3.eu-central-1.amazonaws.com | `pl.load("kitti_raw_2011_09_26_drive_0001")` |
| [Stanford armadillo (Open3D demo mesh)](https://pardesline.github.io/pardesline/datasets/open3d_armadillo/) | mesh (mesh) | 7 MB | see source | Open3D data | `pl.load("open3d_armadillo")` |
| [Stanford bunny (Open3D demo mesh)](https://pardesline.github.io/pardesline/datasets/open3d_bunny/) | mesh (mesh) | 3 MB | see source | Open3D data | `pl.load("open3d_bunny")` |
| [Open3D ICP demo: three indoor point-cloud fragments](https://pardesline.github.io/pardesline/datasets/open3d_icp_demo/) | points (points) | 6 MB | see source | Open3D data | `pl.load("open3d_icp_demo")` |
<!-- datasets-table:end -->

"Size" is the whole source; one sample costs its own size. "See source" means the data owner states terms outside a standard licence; `ds.describe()` prints them and the loader warns. Not bundled, and why: BraTS (Synapse data-use agreement), ModelNet, ShapeNet and ScanNet (registration-gated downloads); they are on the [Datasets wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Adataset) list.

What standardization and the manifest give you: every role is typed (`volume`, `labels`, `mesh`, `points`, `splat`, `image`, `transform`), with frame (LPS, sensor, Y-up), units (mm, m), label names, raw-array layouts, licence, citation and provenance; label maps become exact surfaces in world coordinates, DICOM series become one volume, `.npy`/`.bin` become point clouds; `ds.export(folder)` writes standard PLY / MetaImage files with sidecars; `ds.split(by="patient")` never leaks a patient across splits. Add a dataset: [CONTRIBUTING.md](CONTRIBUTING.md#adding-a-dataset) and [docs/datasets.md](docs/datasets.md).

## 🧠 Algorithms & models

Every row is a public capability of the package today. "Works on" names the object types from the table above. "Validated on" names the bundled data an example or test exercised; a blank cell means the method is covered by generated-data tests only.

**Classical algorithms** (73 methods in 19 catalog modules; `pl.describe("module.method")` prints every parameter with its range)

| Task | High-level call | Underlying method | Works on | Validated on | Docs |
|---|---|---|---|---|---|
| Rigid registration of point clouds | `target.align(moving)` | RANSAC on FPFH features, then point-to-plane ICP (Open3D) | points, mesh | Stanford bunny, 35° / 70 % overlap / 0.5 % noise: 0.14° residual ([example](examples/icp_registration_bunny)) | [registration](docs/catalog.md) |
| Rigid / affine / B-spline / demons registration of volumes | `fixed.align(moving)` | SimpleITK `ImageRegistrationMethod`, Mattes MI, geometry initialisation | volume | RIRE CT/MR ([example](examples/register_ct_mr_rire)) | [simpleitk_registration](docs/catalog.md) |
| Non-rigid registration of point clouds | `pl.run("deformable_registration.cpd_deformable", ...)` | Coherent Point Drift (pycpd), Gaussian deformation | points | | [deformable_registration](docs/catalog.md) |
| Surface reconstruction | `points.to_mesh()` | Poisson (density-trimmed), ball pivoting, alpha shape, convex hull | points | Stanford bunny ([example](examples/poisson_reconstruction_bunny)) | [point_cloud_reconstruction](docs/catalog.md) |
| Label map to mesh | `mask.to_mesh(label=k)` | marching cubes in world coordinates (VTK) | labels, volume | MSD hippocampus ([example](examples/hippocampus_mask_to_mesh)) | [object model](docs/catalog.md#the-object-model) |
| Threshold segmentation of volumes | `volume.segment(lower, upper)` | Otsu / manual threshold, connected components, watershed (SimpleITK) | volume | MSD spleen ([example](examples/spleen_ct_threshold_segmentation)) | [simpleitk_segmentation](docs/catalog.md) |
| Point cloud cleaning and downsampling | `points.clean()`, `points.downsample(voxel_size)` | statistical / radius outlier removal, voxel grid (Open3D) | points | Stanford bunny ([example](examples/poisson_reconstruction_bunny)) | [point_cloud_processing](docs/catalog.md) |
| Point cloud segmentation | `points.segment(eps, min_points)` | DBSCAN, RANSAC plane | points | | [point_cloud_segmentation](docs/catalog.md) |
| LiDAR scenes | `sweep.run("lidar_scene_detection.object_clustering")` | ground plane RANSAC, DBSCAN objects, height colouring; LiDAR-camera fusion | points | KITTI drive ([example](examples/kitti_lidar_ground_and_objects)) | [lidar_scene_detection](docs/catalog.md) |
| Mesh processing | `mesh.decimate()`, `mesh.smooth()`, `mesh.clean()` | quadric decimation, subdivision, Laplacian / Taubin smoothing, hole filling, normals (Open3D, PyVista) | mesh | MSD hippocampus ([example](examples/hippocampus_mask_to_mesh)) | [mesh_processing](docs/catalog.md), [pyvista_mesh_processing](docs/catalog.md) |
| Mesh to points, voxels, SDF | `mesh.to_points()`, `voxel_to_mesh`, `sdf.compute_sdf` | Poisson-disk sampling, voxelisation, signed distance fields, occupancy | mesh, points | Stanford bunny ([example](examples/points_to_gaussians_bunny)) | [sdf](docs/catalog.md) |
| Volume processing | `volume.run("pyvista_volume_processing.pv_slice_orthogonal")` | contour, slices, threshold, geometry extraction (PyVista) | volume | | [pyvista_volume_processing](docs/catalog.md) |
| Geometry analysis | `pl.run("pyvista_analysis.pv_distance", ...)` | curvature, mesh-to-mesh distance, feature edges, scalar statistics | mesh, points | | [pyvista_analysis](docs/catalog.md) |
| Features | `points.normals()`, `features_extraction.fpfh_features` | normals, FPFH, curvature | points | | [features_extraction](docs/catalog.md) |
| Collision | `collision_detection.sdf_collision`, `penetration_depth` | SDF-based collision and penetration depth | mesh | | [collision_detection](docs/catalog.md) |
| Stereo | `stereo_3d_reconstruction.depth_colorization`, `depth_filter` | depth maps to coloured clouds | image | | [stereo_3d_reconstruction](docs/catalog.md) |

**Deep-learning models** (reference implementations and expert guides; no weights are shipped and there is no inference API yet. The direction: one-line pretrained model access through the same manifest and loader pattern as datasets, see the [model registry tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22).)

| Task | What ships today | Model | Works on | Validated on | Docs |
|---|---|---|---|---|---|
| Point cloud semantic segmentation | `make_point_dataset.py` + `pointnet_seg.py` (train / eval / infer) | PointNet (Qi et al. 2017), PointNet++ notes | points from any label map | MSD hippocampus ([example](examples/pointnet_hippocampus)) | [pointnet-segmentation](skills/pointnet-segmentation/SKILL.md) |
| Dense visual features | `dinov3_features.py`, `dinov3_faster_rcnn.py` | DINOv3 / DINOv2 frozen backbones (transformers), Faster R-CNN head | image | KITTI camera frame ([example](examples/dinov2_features_kitti)) | [dinov3-dense-features](skills/dinov3-dense-features/SKILL.md) |
| Self-supervised pretraining on volumes | `jepa3d_pretrain.py` | 3D JEPA (context encoder, predictor, EMA target) | volume | MSD hippocampus ([example](examples/jepa_hippocampus)) | [jepa-pretraining](skills/jepa-pretraining/SKILL.md) |
| Anomaly detection by reconstruction | `vae_anomaly.py` (train / score, AUROC) | convolutional VAE | image | MSD hippocampus slices ([example](examples/vae_anomaly_hippocampus)) | [vae-anomaly-detection](skills/vae-anomaly-detection/SKILL.md) |
| Supervised 3D medical segmentation | `prepare_nnunet_dataset.py` (any dataset to nnU-Net v2 raw layout) | nnU-Net and the model families that win MSD / AMOS / KiTS | volume + labels | MSD spleen (skill script) | [medical-segmentation-models](skills/medical-segmentation-models/SKILL.md) |
| Gaussian splats from points | `points_to_gaussians.py` | 3DGS initialisation (means, log-scales, SH colour) | points, mesh | Stanford bunny ([example](examples/points_to_gaussians_bunny)) | [gaussian-splatting](skills/gaussian-splatting/SKILL.md) |

**Metrics & evaluation**

| Task | Call | Metrics | Validated on | Docs |
|---|---|---|---|---|
| Segmentation and surface quality | `metrics3d.py` (`dice`, `iou`, `hd95`, `assd`, `surface_dice`, `volume_error`) | label-map metrics with spacing, in mm | liver tumour, three radiologists ([example](examples/metrics_liver_interobserver)) | [evaluation-metrics-3d](skills/evaluation-metrics-3d/SKILL.md) |
| Registration and point sets | `chamfer`, `f_score`, `pose_error`; `registration_eval.py` | fitness, inlier RMSE, rotation / translation error, Chamfer, HD95 | Stanford bunny ([example](examples/icp_registration_bunny)) | [point-cloud-registration](skills/point-cloud-registration/SKILL.md) |

### Defaults that work on real data

Same task, same two clouds: the Stanford bunny sampled to 20 000 points, and a second "scan" rotated by 35°, trimmed to 70 % overlap and jittered with 0.5 % noise of the bounding-box diagonal. Left, Open3D's `registration_icp` the way the tutorial calls it; right, `target.align(moving)`.

<table>
<tr>
<th>Open3D ICP, textbook call</th>
<th>pardesline, one call</th>
</tr>
<tr>
<td>

```python
reg = o3d.pipelines.registration.registration_icp(
    moving, target, 0.02, np.eye(4), TransformationEstimationPointToPoint()
)
```

</td>
<td>

```python
aligned = target.align(moving)
```

</td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/icp_registration_bunny/textbook_defaults.png" width="420" alt="Two bunny point clouds still misaligned after textbook ICP, 32 degrees apart"></td>
<td><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/icp_registration_bunny/pardesline_defaults.png" width="420" alt="Two bunny point clouds overlapping after pardesline registration, 0.14 degrees apart"></td>
</tr>
<tr>
<td>rotation error <b>32.0°</b>, fitness 0.98 (misleading: it counts pairs within 0.02, which the identity start already satisfies for the overlap), nearest-neighbour RMSE 7.1 mm</td>
<td>rotation error <b>0.14°</b>, inlier RMSE 0.9 mm, nearest-neighbour RMSE 1.4 mm (the noise floor)</td>
</tr>
</table>

What the one call sets, and why:

- `voxel_size = 0` → 1.3 % of the bounding-box diagonal: the feature scale follows the object, not a hard-coded 0.05 m that is wrong for a 15 cm bunny and for a 15 m facade alike.
- `distance_threshold_factor = 1.5 × voxel`: RANSAC accepts a correspondence within one and a half cells; tighter rejects true matches on noisy scans, looser lets outliers in.
- RANSAC on FPFH first, ICP second: ICP alone is a local optimiser and needs a start within a few degrees; a 35° offset is outside its basin, which is why the textbook call stops where it started.
- `icp_estimation_method = point_to_plane`, `icp_threshold_factor = 1.5 × voxel` then `refine_threshold_factor = 0.4 × voxel`: coarse to fine, so the last iterations are not pulled by the 30 % of points that have no counterpart.
- Every value is in the sidecar `aligned.provenance[-1]["params"]`, and `pl.describe("registration.ransac_icp_pipeline")` prints the ranges to override them.

Numbers come from [examples/icp_registration_bunny/run.py](examples/icp_registration_bunny/run.py) (`result.json` is committed next to the images). The written proof for every algorithm family, failure mode by failure mode, is the docs page [Why our defaults work](https://pardesline.github.io/pardesline/algorithms/why-our-defaults-work/).

### Validated on real cases

| Use case | Domain | Data characteristics | Algorithm | What the defaults handle | Example |
|---|---|---|---|---|---|
| Multimodal head registration | medical imaging | CT 0.65 mm × 4 mm slices vs MR 1.25 mm × 4 mm, different fields of view | `simpleitk_registration.rigid` | anisotropic spacing, intensity ranges that do not match (mutual information), initial offset of 40 mm | [register_ct_mr_rire](examples/register_ct_mr_rire) |
| Second scan of a part | industrial 3D scanning (public stand-in) | partial overlap 70 %, 0.5 % noise, unknown pose | `registration.ransac_icp_pipeline` | scale-free feature radius, global init, coarse-to-fine ICP | [icp_registration_bunny](examples/icp_registration_bunny) |
| Organ surface from a label map | medical imaging | 1 mm isotropic MRI label map, two labels | `LabelMap.to_mesh` + Taubin smoothing | exact label boundary in LPS mm, voxel staircase removed without shrinking | [hippocampus_mask_to_mesh](examples/hippocampus_mask_to_mesh) |
| Street scene from a LiDAR sweep | automotive LiDAR | 120 000 points, headerless `(N, 4)` binary, ground plane tilted | `lidar_scene_detection.object_clustering` | layout from the manifest, RANSAC ground at 0.3 m, DBSCAN 0.5 m | [kitti_lidar_ground_and_objects](examples/kitti_lidar_ground_and_objects) |

These run on public data that stands in for the industrial and medical scans the defaults were tuned on. Real cases from users are collected in [examples/real_cases/](examples/real_cases/README.md): a template and a tracking issue, so that every claim on this page stays reproducible.

## How it compares

pardesline is the dataset layer and the domain-level API on top of these libraries, not a replacement: it calls Open3D, PyVista, VTK and SimpleITK and hands you their objects. Each cell is checked against the project's own documentation; corrections are welcome as issues.

| | pardesline | [Open3D](https://www.open3d.org/) | [PyVista](https://docs.pyvista.org/) | [SimpleITK](https://simpleitk.org/) | [trimesh](https://trimesh.org/) | [MONAI](https://monai.io/) | [TorchIO](https://torchio.readthedocs.io/) | [HF datasets](https://huggingface.co/docs/datasets) |
|---|---|---|---|---|---|---|---|---|
| One-line access to public 3D / medical datasets | 43 manifests: MSD, TCIA, Zenodo, S3, Hugging Face, OpenNeuro, KITTI | demo meshes and fragments (`open3d.data`) | example meshes and volumes (`pyvista.examples`) | notebook data fetcher | no | `DecathlonDataset`, `TciaDataset`, `MedNISTDataset` | IXI, EPISURG and other medical sets | any Hub repo, files untyped |
| Point clouds, meshes **and** volumes in one object | yes, plus splats and raw arrays | points, meshes, voxel grids | meshes, grids, volumes | volumes | meshes | volumes (tensors) | volumes | no |
| Standardization (frame, units, labels, spacing) | manifest + sidecar, never guessed | no | no | header-aware | no | transforms (`Spacingd`, `Orientationd`) | transforms (`Resample`, `ToCanonical`) | no |
| Licence and provenance attached to the data | yes | no | no | no | no | no | no | licence field on the card |
| High-level, domain-vocabulary API | `align`, `segment`, `to_mesh`, `clean`, `scan` | algorithm names | VTK filter names | ITK filter names | geometry names | transforms and bundles | transforms | no |
| Defaults tied to the data scale | voxel from bounding box, thresholds as multiples | fixed numbers in calls | filter defaults | filter defaults | n/a | per bundle | per transform | n/a |
| Validated on real industrial / medical data | public stand-ins + `examples/real_cases/` mechanism | tutorials | gallery | notebooks | tests | model zoo benchmarks | papers | n/a |
| Classical 3D algorithms | 73 (through the libraries) | yes | yes | yes | yes | some (via ITK/MONAI transforms) | no | no |
| One-line pretrained model access | **roadmap** (model registry) | Open3D-ML weights | no | no | no | Model Zoo bundles | no | via `transformers` |
| Local MCP server for AI agents | 14 tools, 20 skills | no | no | no | no | no | no | no |
| Licence | Apache-2.0 | MIT | MIT | Apache-2.0 | MIT | Apache-2.0 | Apache-2.0 | Apache-2.0 |

Full page with the sources of each cell: [docs comparison](https://pardesline.github.io/pardesline/comparison/).

## Examples gallery

Each folder is one self-contained script that downloads what it needs, runs, and writes its images next to itself. Titles follow `<algorithm or model> on <dataset>`. Run any of them with `python examples/<folder>/run.py`.

<table>
<tr>
<td align="center" width="33%"><a href="examples/register_ct_mr_rire"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/register_ct_mr_rire/rire_ct_mr.png" width="280" alt="CT slice and registered MR overlay"><br><b>SimpleITK rigid registration on RIRE</b></a><br><sub>CT fixed, MR T1 moving, 21 s cold</sub></td>
<td align="center" width="33%"><a href="examples/icp_registration_bunny"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/icp_registration_bunny/pardesline_defaults.png" width="280" alt="Two bunny point clouds aligned"><br><b>RANSAC + ICP on the Stanford bunny</b></a><br><sub>textbook ICP vs one call, with numbers</sub></td>
<td align="center" width="33%"><a href="examples/hippocampus_mask_to_mesh"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/hippocampus_mask_to_mesh/hippocampus.png" width="280" alt="Hippocampus meshes over MRI slices"><br><b>Label map to mesh on MSD hippocampus</b></a><br><sub>exact boundaries, Taubin smoothing, STL + sidecar</sub></td>
</tr>
<tr>
<td align="center"><a href="examples/poisson_reconstruction_bunny"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/poisson_reconstruction_bunny/bunny_poisson.png" width="280" alt="Bunny points and the Poisson surface"><br><b>Poisson reconstruction on the Stanford bunny</b></a><br><sub>sample, clean, rebuild a surface</sub></td>
<td align="center"><a href="examples/spleen_ct_threshold_segmentation"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/spleen_ct_threshold_segmentation/spleen_ct.png" width="280" alt="Threshold segmentation vs reference spleen label"><br><b>Threshold segmentation on MSD spleen</b></a><br><sub>the honest baseline a model has to beat</sub></td>
<td align="center"><a href="examples/kitti_lidar_ground_and_objects"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/kitti_lidar_ground_and_objects/kitti_objects.png" width="280" alt="KITTI sweep with ground removed and objects coloured"><br><b>Ground removal + clustering on KITTI</b></a><br><sub>one 2 MB sweep out of a 459 MB zip</sub></td>
</tr>
<tr>
<td align="center"><a href="examples/atlas_label_transfer_bunny"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/atlas_label_transfer_bunny/atlas_transfer.png" width="280" alt="Bunny atlas in grey with the scan coloured by transferred labels"><br><b>Atlas label transfer on the Stanford bunny</b></a><br><sub>register a labelled atlas, transfer labels: 99.4 % agreement</sub></td>
<td align="center"><a href="examples/points_to_gaussians_bunny"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/points_to_gaussians_bunny/bunny_splats.png" width="280" alt="Bunny Gaussian centres coloured by height"><br><b>Gaussian splats on the Stanford bunny</b></a><br><sub>50 000 points to a 3DGS PLY that opens in gsplat</sub></td>
<td align="center"><a href="examples/vae_anomaly_hippocampus"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/vae_anomaly_hippocampus/vae_anomaly.png" width="280" alt="Test slices, VAE reconstructions and residual maps with scores; lesion slices score highest"><br><b>VAE anomaly detection on MSD hippocampus slices</b></a><br><sub>lesion slices score 0.59 and 0.64, normals at most 0.33</sub></td>
</tr>
<tr>
<td align="center"><a href="examples/pointnet_hippocampus"><b>PointNet on MSD hippocampus</b></a><br><sub>40 cases, 40 epochs on CPU: 0.97 mIoU anterior / posterior</sub></td>
<td align="center"><a href="examples/jepa_hippocampus"><b>3D JEPA on MSD hippocampus</b></a><br><sub>self-supervised pretraining, laptop-sized</sub></td>
<td align="center"><a href="examples/dinov2_features_kitti"><img src="https://raw.githubusercontent.com/pardesline/pardesline/main/examples/dinov2_features_kitti/dinov2_kitti.png" width="280" alt="KITTI camera frame above its PCA-coloured DINOv2 patch features"><br><b>DINOv2 / DINOv3 features on KITTI</b></a><br><sub>frozen backbone, PCA-coloured patch features</sub></td>
</tr>
</table>

Also: [Dice / HD95 between three radiologists on the liver tumour CT](examples/metrics_liver_interobserver) (0.82 to 0.85 Dice, 2.5 mm HD95: the inter-observer ceiling). The PyTorch examples need `pip install torch` (CPU is enough); DINOv3 weights need the licence accepted on the Hub, DINOv2 does not. Index and expected runtimes: [examples/README.md](examples/README.md).

## 🤖 MCP: give it to an AI agent

```bash
pip install "pardesline[mcp]"
claude mcp add pardesline -- pardesline mcp        # Claude Code; Claude Desktop, Cursor, Gemini CLI, Codex: {"command": "pardesline", "args": ["mcp"]}
```

The server exposes the datasets, the algorithms, the object model and the twenty skills as tools: `list_datasets`, `describe_dataset`, `list_samples`, `load_sample`, `scan_dataset`, `confirm_dataset`, `export_dataset`, `list_methods`, `describe_method`, `run_method`, `describe_object`, `to_mesh`, `list_skills`, `get_skill`. An agent can browse the catalog, fetch one sample, run a pipeline, read the expert guide for the method it is about to use, and export standard files. Questions the package will not guess (licence, units, array layout) come back as JSON for the agent to relay to the human. No account, nothing leaves the machine. Client configurations and the full contract: [docs/mcp.md](docs/mcp.md).

## Roadmap

Vote with 👍 on the tracking issue; comment with your dataset, model or use case.

- [ ] **Model registry**: one-line access to pretrained 3D and medical models (DINOv3, SAM-3D-style segmenters, JEPA encoders, PointNet, segmentation nets) through a model manifest (source, weights URI, licence, input type, task, memory needs, provenance) and `pl.load_model(...)` / `pl.run(model, dataset)`, the same pattern as datasets. [Tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22model+registry%22)
- [ ] **Gaussian splats as a first-class kind** (`Splat`: load, render, convert to points, metrics). [Tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+splats)
- [ ] **More datasets**: BraTS (behind the user's Synapse credentials), VerSe 2020, the remaining public TCIA collections, ModelNet / ShapeNet / ScanNet once their gating can be honoured. [Datasets wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Adataset)
- [ ] **Models wanted**: model manifests contributors can write before the runner exists. [Models wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Amodel)
- [ ] **Benchmarks**: package defaults vs upstream defaults on the bundled data, numbers regenerated by CI. [Tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+benchmarks)
- [ ] **A pardesline organisation on Hugging Face** mirroring the permissive datasets with `pip install pardesline` as the documented loader. [Tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+%22hugging+face%22)
- [ ] **Deformable registration and TotalSegmentator-class segmentation behind the same calls** (`align(mode="deformable")`, `segment(model=...)`). [Tracking issue](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Aroadmap+segment)

## Community and contributing

- Questions and show-and-tell: [GitHub Discussions](https://github.com/pardesline/pardesline/discussions).
- Bugs and requests: [issues](https://github.com/pardesline/pardesline/issues/new/choose), with templates for bugs, features, dataset requests and algorithm or model requests.
- First contribution: [good first issues](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22), most of them "add dataset X" or "add algorithm Y" with a template to copy.
- How to set up, test, add a dataset, an algorithm or a model: [CONTRIBUTING.md](CONTRIBUTING.md). Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security: [SECURITY.md](SECURITY.md).

## Citation

If pardesline helps your research, cite it ([CITATION.cff](CITATION.cff), also behind the "Cite this repository" button):

```bibtex
@software{tabet_pardesline_2026,
  author  = {Tabet, Jonathan},
  title   = {pardesline: 3D vision and medical imaging in one Python package},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/pardesline/pardesline},
  license = {Apache-2.0}
}
```

Cite the datasets you use as well: `ds.citation` returns the reference the data owner asks for.

## Acknowledgements and licence

pardesline stands on [Open3D](https://github.com/isl-org/Open3D), [PyVista](https://github.com/pyvista/pyvista) and [VTK](https://vtk.org/), [SimpleITK](https://github.com/SimpleITK/SimpleITK), [NumPy](https://numpy.org/), [SciPy](https://scipy.org/), [scikit-image](https://scikit-image.org/), [pycpd](https://github.com/siavashk/pycpd), [httpx](https://www.python-httpx.org/), [pydantic](https://docs.pydantic.dev/), [loguru](https://github.com/Delgan/loguru), [huggingface_hub](https://github.com/huggingface/huggingface_hub) and the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk). The datasets belong to their authors and institutions; every manifest carries the citation they ask for and the licence they state.

Apache License 2.0 for the package; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Datasets keep their own licences: `ds.describe()` prints them.

<p align="center"><a href="https://star-history.com/#pardesline/pardesline&Date"><img src="https://api.star-history.com/svg?repos=pardesline/pardesline&type=Date" width="600" alt="Star history chart of pardesline/pardesline"></a></p>
