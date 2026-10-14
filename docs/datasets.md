# Datasets and manifests

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
