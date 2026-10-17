---
title: "Using pardesline: where everything is"
description: "START HERE for the open-source `pardesline` Python package (Apache-2.0): 3D vision and medical imaging on the user's own machine. One typed object for poin"
---

# Using pardesline: where everything is

# Using pardesline

`pardesline` (import as `pl`) is one Python package for point clouds, meshes,
medical volumes and label maps. Everything under `pl.load` / `pl.run` executes
on the machine that runs Python; nothing leaves it. The cloud client is
optional and separate (`pardesline.cloud`).

## Install (tell the user exactly this)

```bash
pip install "pardesline[all]"       # Open3D + PyVista + SimpleITK + huggingface_hub
pip install "pardesline[local]"     # point clouds, meshes, SDF, LiDAR (Open3D, PyVista)
pip install "pardesline[medical]"   # volumes, DICOM, registration, segmentation (SimpleITK + PyVista)
pip install "pardesline[hf]"        # pl.load("hf://...")
pip install pardesline              # catalog + object model + cloud client only, no native libs
```

Python 3.10 to 3.12 for `[local]` (Open3D 0.19 has no 3.13 wheels). A missing
library raises `pl.MissingDependency` whose message names the extra to install.

## The three entry points

```python
import pardesline as pl

obj = pl.load("scan.ply")  # Object (PointCloud / Mesh / Volume / LabelMap ...)
out = obj.run("point_cloud_processing.voxel_downsample", voxel_size=0.02)  # new Object
res = pl.run("point_cloud_processing", "voxel_downsample", "scan.ply", voxel_size=0.02)  # RunResult
ds = pl.load("rire_brain")  # Dataset: samples with typed roles, fetched on access
```

| You want to | Use | Skill |
|---|---|---|
| run one of the 73 algorithms, see its parameters | `pl.run`, `pl.describe("module.method")`, CLI `pardesline run` | catalog-and-run |
| chain operations on a file, keep frame/licence/provenance | `pl.load(file)` then `.downsample() .poisson() .decimate() ...` | object-model |
| segment a volume, turn a label into a surface, register two scans | `Volume.segment()`, `LabelMap.to_mesh(label)`, `Volume.align(moving)` | object-model, medical-volumes |
| load a public dataset, a Hugging Face repo, a bucket, a TCIA collection or your own folder | `pl.load("msd_task02_heart")`, `pl.load("hf://org/name/sub")`, `pl.load("tcia://Pancreas-CT")`, `pl.load("s3://openneuro.org/ds000001")`, `pl.load("/data/study")` | datasets-and-manifests, scanning-private-folders |
| read a raw `.npy` / `.bin` array, standardise a dataset | `pl.load("sweep.bin", layout={...})`, `ds.export(folder)`, `pardesline export` | object-model, datasets-and-manifests |
| write a manifest, answer the scan's questions | `pl.scan(folder)`, `pl.load(folder, license=..., units=..., labels=...)` | scanning-private-folders |
| share a result, run on the hosted GPU, open a browser viewer | `pl.login()`, `pl.upload`, `pl.share`, `pardesline.cloud` | cloud-client |
| give an AI agent (Claude, Gemini, Cursor, Codex) the datasets and algorithms through MCP | `pardesline mcp`, `.mcp.json`, tools `load_sample`, `scan_dataset`, `run_method` | mcp-server |
| choose a 3D representation, convert between them | conversion matrix, memory, pitfalls | 3d-representations |
| align two clouds or an atlas and judge the result | RANSAC + FPFH + ICP parameters, metrics, CPD | point-cloud-registration, atlas-label-transfer |
| register CT with MRI (or PET, CBCT) | Mattes MI, initialiser, pyramid, TRE | multimodal-rigid-registration |
| train or use a segmentation model on volumes or points | nnU-Net export, TotalSegmentator, PointNet data contract | medical-segmentation-models, pointnet-segmentation |
| use foundation-model features, pretrain without labels, detect anomalies | frozen DINOv3 heads, JEPA, VAE residual maps | dinov3-dense-features, jepa-pretraining, vae-anomaly-detection |
| write or read Gaussian splats | points -> 3DGS, PLY layout, training | gaussian-splatting |
| report a result honestly | Dice / HD95 / NSD / chamfer / TRE / AUROC, per-case statistics | evaluation-metrics-3d |
| add an algorithm or a manifest to the package | `src/pardesline/ops/<module>/`, `catalog/data/<module>.json`, `data/manifests/` | contributing-algorithms |

## Rules the package enforces (do not fight them, explain them)

- **Never guess silently.** A format that carries no unit or axis convention
  (PLY, STL, OBJ, PCD, VTK grids) gives `obj.units is None`. Declare with
  `obj.with_frame("Z-up", "mm")` or a manifest. Volumes read LPS/mm from their
  header; glTF is Y-up/m by specification.
- **Parameters are validated before anything runs** against the catalog
  (type, range, choices, unknown names with a "did you mean"). Read the error:
  it lists what is accepted.
- **Two-input methods need `moving=`** (registration). Without it the call
  raises instead of self-aligning a synthetic copy.
- **A folder needs a confirmed manifest.** `pl.load(folder)` raises
  `NeedsConfirmation` listing licence / units / labels questions; answer them in
  the call, in the saved draft, interactively, or pass `assume=True`.
- **Licences travel with the data.** `ds.license.describe()`; bundled public
  datasets whose terms are not established say `TO CONFIRM`.

## Errors (all derive from `pl.PardesLineError`, each has `.code`)

`ParameterError` (bad or unknown parameter), `CatalogError` (unknown
module/method), `RunError` (script failed: `.returncode`, `.log`, `.command`),
`MissingDependency` (install an extra), `ManifestError`, `FetchError`
(download or checksum), `NeedsConfirmation` (`.questions`, `.draft_path`).
`FileNotFoundError` for missing inputs.

## Quick facts

19 modules, 73 methods, 371 parameters (`pl.catalog()`), 43 bundled datasets
(`pl.datasets()`: 35 medical - DICOM, NIfTI, MetaImage, npz, STL, splats -
over https, Hugging Face, remote archives by HTTP Range, S3, TCIA and URL
indexes), outputs default to `pl.output_dir()` (system temp,
change with `pl.set_output_dir`), downloads cache in `~/.cache/pardesline`
(`PARDESLINE_CACHE`). `pl.o3d`, `pl.pv`, `pl.sitk`, `pl.np` are the real
libraries when installed, the cloud-executed mirrors otherwise.

<sub>Source: `skills/using-pardesline/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-14.</sub>
