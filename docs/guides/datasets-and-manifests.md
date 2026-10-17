---
title: "Datasets and manifests"
description: "Load datasets with pardesline by manifest instead of per-dataset code: the 43 bundled datasets (35 medical: the ten MSD tasks, AMOS, TotalSegmentator CT/MR"
---

# Datasets and manifests

# Datasets and manifests

`pl.load` never knows a dataset; it knows a **manifest**. A manifest says
where the files come from (with checksums or a hub revision), under which
terms, how files group into samples, and what the files cannot say by
themselves (frame, units, label meanings, the layout of a raw array). Same
code path for a bundled public dataset, a Hugging Face repo, a remote
archive and a private folder.

## Bundled datasets (`pl.datasets()`, `pl.describe(name)`, `pardesline datasets`)

| Name | Content | Roles | Source |
|---|---|---|---|
| `rire_brain` | RIRE training_001: CT + MR-T1 of one brain | `ct`, `mr_t1` | https, 19 MB |
| `popi_lung_4dct` | POPI thorax 4D-CT, phases `phase_00`..`phase_50`, mask on phase 00 | `ct`, `mask` `{1: body, 2: lungs}` | https, 500 MB |
| `liver_tumor_patient01` | abdominal CT + three radiologists' tumour masks | `ct`, `rad01` `rad02` `rad03` `{1: tumor}` | https, 2 MB |
| `visible_human_head_mri` | NLM Visible Human head MRI | `mri` | https, 2 MB |
| `open3d_bunny`, `open3d_armadillo` | Stanford meshes via `open3d.data` | `mesh` | open3d |
| `open3d_icp_demo` | Redwood fragments, pairs `pair_0_1`, `pair_1_2` | `source`, `target` (points, sensor, m) | open3d |
| `msd_task02_heart` | MSD Task02: 20 labelled + 10 test cardiac MRIs, left atrium | `mri`, `mask` `{1: left_atrium}`; field `split` Tr/Ts | archive (tar on S3, 456 MB) |
| `amos22` | AMOS 22: 500 CT + 100 MRI, 15 abdominal organs | `image`, `mask` (15 labels); `split` Tr/Va/Ts | archive (zip64 on Zenodo, 24 GB) |
| `kitti_raw_2011_09_26_drive_0001` | one KITTI raw drive: 108 Velodyne sweeps + stereo images | `lidar` (.bin, layout), `image_left`, `image_right`, `calibration` | archive (zip on S3, 459 MB) |
| `hf_openmind` | OpenMind head MRI, one OpenNeuro study (`OpenMind/ds000001`) | `t1w`, `t2w`, `deface_mask`, `anatomy_mask` | hf `MIC-DKFZ/OpenMind` |
| `hf_nsclc_radiomics` | NSCLC-Radiomics (TCIA) 422 lung CTs + organ/tumour masks | `ct`, `mask` (6 labels), `gtv`, `lung_left`, `lung_right`, `heart`, `esophagus`, `spinal_cord` | hf `farrell236/NSCLC-Radiomics-NIFTI` |
| `hf_objaverse_glb_shard` | Objaverse, one shard of 5 000 glTF meshes | `mesh` (Y-up, m) | hf `allenai/objaverse` |
| `hf_3d_arena` | 3D Arena: 29 image-to-3D generators x ~100 images | `mesh`, `splat`, `preview` | hf `3d-arena/3d-arena` |
| `hf_uniocc_carla_mini` | UniOcc CARLA 10 Hz mini: LiDAR, cameras, occupancy grids | `lidar`, `occupancy` (.npz grid), `ego_to_world`, `camera_0..3`, `bev` | hf `tasl-lab/uniocc` |
| `hf_kitti360_gs_subset` | 16 KITTI-360 chunks: LiDAR points + Gaussian-splat arrays | `points`, `point_segments`, `gaussian_*` (.npy, layouts) | hf `GaussianWorld/kitti_360_subset_chunk_gs_preprocessed` |
| `msd_task01_braintumour`, `msd_task03_liver`, `msd_task04_hippocampus`, `msd_task05_prostate`, `msd_task06_lung`, `msd_task07_pancreas`, `msd_task08_hepaticvessel`, `msd_task09_spleen`, `msd_task10_colon` | the other MSD tasks, same layout as Task02 | `ct` or `mri`, `mask` (task labels); field `split` Tr/Ts | archive (tar on S3) |
| `totalsegmentator_ct` | 1 228 CTs, 117 structures | `ct` + one labels role per structure (`liver`, `vertebrae_l3`, `rib_left_6`...) | archive (zip on Zenodo, 24 GB) |
| `totalsegmentator_mri` | 298 MRIs, 56 structures | `mri` + one labels role per structure | archive (zip on Zenodo) |
| `luna16` | 888 thorax CTs (MetaImage), ten folds | `ct`; field `subset` | archive (ten zips on Zenodo) |
| `ixi_brain_mri` | ~600 healthy brains | `t1`, `t2`, `pd`, `mra` | archive (four tars, Imperial College) |
| `verse19_spine` | 160 spine CTs | `ct`, `mask` (28 vertebra labels), `centroids` (json); field `split` | archive (three zips, BoneScreen S3) |
| `spider_lumbar_mri` | 447 lumbar MRIs | `t1`, `t2`, `t2_space` + `*_mask` (vertebrae / discs / canal) | archive (two zips on Zenodo) |
| `chaos_abdomen` | 20 CT + 20 MR patients as DICOM series | `ct`, `mr_t1_inphase`, `mr_t1_outphase`, `mr_t2_spir`; ids `CT/1`, `MR/1` | archive (zip on Zenodo) |
| `tcia_pancreas_ct`, `tcia_lidc_idri`, `tcia_nsclc_radiomics_dicom`, `tcia_prostate_3t` | TCIA collections as DICOM series | `ct` / `t2` (DICOM folder), `seg`, `rtstruct` (files) | tcia (NBIA API) |
| `openneuro_ds000228` | T1w MRI of 155 children and adults | `t1w` | s3 `openneuro.org/ds000228` |
| `hf_kits23` | 489 kidney-tumour CTs | `ct`, `mask` `{1: kidney, 2: tumor, 3: cyst}` | hf `neheller/KiTS-Challenge-Imaging` |
| `hf_abdomenatlas_mini` | first 100 of 5 195 abdominal CTs (gated, token) | `ct`, `combined_labels` + nine organ masks | hf `AbdomenAtlas/AbdomenAtlas1.0Mini` |
| `hf_ct_rate_valid` | first 20 validation chest CTs (gated, token) | `ct` | hf `ibrahimhamamci/CT-RATE` |
| `hf_biomedsegfm_3d_val` | 2 144 CT / MRI / PET / US3D / microscopy volumes as npz | `image`, `mask` (npz keys imgs / gts); field `modality` | hf `junma/CVPR-BiomedSegFM` |
| `medshapenet` | 106 101 STL shapes | `mesh`; fields `case`, `structure` | urllist (sciebo) |
| `c3vd_endoscopy_splats` | ten colonoscopy scenes | `splat` (3DGS PLY), `points` | archive (zip on Zenodo) |

Licences: the https/open3d excerpts say **TO CONFIRM** (terms not established
by the package authors). The hub/archive manifests carry the id the source
states (MSD and AMOS: CC-BY-SA 4.0 from their `dataset.json`; OpenMind CC-BY
4.0; NSCLC CC-BY 3.0; Objaverse ODC-By with per-object CC terms; 3D Arena and
UniOcc MIT; KITTI and KITTI-360 CC-BY-NC-SA 3.0, `commercial: false`). Always
read `ds.license.describe()` to the user before redistribution or commercial
use. Medical ones need `[medical]`, Open3D ones `[local]`, `hf_*` need `[hf]`.

```python
ds = pl.load("msd_task02_heart")  # nothing downloaded yet; the tar is indexed by HTTP Range (32 KB)
ds.describe()
labelled = ds.filter(split="Tr")  # 20 cases
s = labelled[0]
atrium = s.mask.to_mesh(label=1)  # fetches two NIfTI files (~15 MB), exact surface in LPS mm
train, test = labelled.split(fractions=(0.8, 0.2), seed=0)

ds = pl.load("hf_nsclc_radiomics")  # lists the repo folder once (cached), 422 patients
ct = ds["LUNG1-001"].ct  # one 36 MB NIfTI through huggingface_hub
ds["LUNG1-001"].mask.labels  # {1: 'esophagus', 2: 'gtv', 3: 'heart', ...}

sweep = pl.load("kitti_raw_2011_09_26_drive_0001")[0].lidar  # .bin decoded through its layout
sweep.frame.describe()  # "sensor, m (manifest)"
objects = sweep.run("ground_removal").run("object_clustering", eps=0.7, min_points=10)
```

## Any public bucket or TCIA collection: `s3://`, `tcia://`

`pl.load("s3://openneuro.org/ds000001")` lists the prefix of a public bucket
(ListObjectsV2, anonymous, paginated, cached, capped at 20 000 keys) and
drafts a manifest; OpenNeuro's licence (CC0 / PDDL) is filled in. When
nothing is left to ask (NIfTI carries its frame) the dataset loads directly.
`pl.load("tcia://Pancreas-CT/CT")` lists the series of a public TCIA
collection through the NBIA API (one entry per series, named
`<PatientID>/<Modality>/<SeriesInstanceUID>/`; the optional `/CT,MR` part
filters modalities); each series downloads as a zip of DICOM files on first
access and becomes a DICOM `Volume`. Restricted collections answer 401 and
are left to the NBIA Data Retriever. A manifest routes modalities to roles
with patterns such as `{id}/CT/{series}` (id = patient) and `{id}/SEG/{series}`.

## Any Hugging Face repo: `hf://org/name[/sub/folder]`

- With a bundled manifest for that repo: loads it. A sub-folder re-scopes the
  listing: `pl.load("hf://MIC-DKFZ/OpenMind/OpenMind/ds000003")`.
- Without one: the package **lists the folder, drafts a manifest and asks**
  exactly as for a private folder (`pl.NeedsConfirmation`): the licence
  (taken from the Hub card when it states one, still marked TO CONFIRM),
  units and frame of formats that carry none, label meanings, and the
  `layout` + `types` of raw arrays. Answer in the call, edit the draft saved
  under `pl.cache_dir()/drafts/`, `interactive=True`, or `assume=True`.
- `pl.scan("hf://org/name/sub")` returns the draft without raising.
- Listing is per sub-folder (`list_repo_tree`), cached on disk for the repo
  commit, capped by `source.max_files` (20 000): a 266 721-file repo such as
  OpenMind is never listed whole (that takes 15 minutes and ends in HTTP 429
  for anonymous clients). Tell the user to set `HF_TOKEN` or run
  `huggingface-cli login` for higher limits and for gated repos; the package
  never scripts past a click-through.

```python
pl.load("hf://acme/scans/raw")
# NeedsConfirmation: hf_acme_scans: 3 question(s) ...
#   - roles.scan.layout: raw/p01/scan.bin is a raw array. What is in it? ...
ds = pl.load(
    "hf://acme/scans/raw",
    types={"scan": "points"},
    layout={"scan": {"dtype": "float32", "shape": "(N,4)", "columns": ["x", "y", "z", "i"]}},
    units={"scan": "m"},
    frame={"scan": "sensor"},
)
```

## Dataset API

- Indexing: `ds[i]`, `ds["sample_id"]`, iteration, `len`, `ds.ids`.
- Subsets (lazy, same source): `ds.take(n)`, `ds.sample(n, seed=0)`,
  `ds.filter(split="Tr")` on sample fields (pattern placeholders become fields).
- `ds.split(by=None, fractions=(0.8, 0.2), seed=0)` -> tuple of Datasets;
  every sample sharing the `by` field (default the manifest `pairing` key)
  lands in one part.
- By role or type: `ds.role("ct")`, `ds.volumes`, `ds.meshes`, `ds.points`
  (iterators), `ds.roles`, `ds.manifest`, `ds.license`, `ds.citation`.
- `ds.fetch_all()` downloads everything now. `ds.export(folder)` writes a
  **standard copy**: raw arrays become PLY / MetaImage through their layout,
  DICOM series one `.mha`, every file with its `.pardesline.json` sidecar,
  plus a local `pardesline.manifest.json` so `pl.load(folder)` reopens it
  without questions. CLI: `pardesline export msd_task02_heart ./heart --take 2`.
- Sample: `s.get("ct")`, `s["ct"]`, `s.ct` (cached), `s.path("ct")` (local
  path after fetch), `s.id`, `s.fields`, `s.license`, `s.describe()`.

Objects from a dataset carry `role`, the dataset licence, the role's frame
(`source="manifest"`, never overriding a header), `labels`, `layout`,
`meta["modality"]`, and a first provenance step `{"step": "load", "dataset",
"sample", "role", "source"}`.

## The manifest schema (pydantic, `extra="forbid"`)

```json
{
  "schema_version": 1,
  "name": "study_a",                       // ^[a-z0-9][a-z0-9_-]*$
  "title": "...", "description": "...",
  "source": {"scheme": "local", "root": "/data/study_a"},
  "license": {"spdx": "CC-BY-4.0", "commercial": true, "source_url": "...", "note": "...",
              "requires_agreement": false, "redistribution": "allowed|forbidden|unknown"},
  "citation": "...", "homepage": "...",
  "pairing": "patient",                     // the field that groups samples for split()
  "roles": {
    "ct":   {"type": "volume", "pattern": "{id}/ct/*.dcm", "frame": "LPS", "units": "mm", "modality": "CT"},
    "mask": {"type": "labels", "pattern": "{id}/seg.nii.gz", "labels": {"1": "left_atrium"}},
    "mesh": {"type": "mesh",   "pattern": "{id}/la.stl", "units": "mm", "frame": "LPS"},
    "lidar": {"type": "points", "pattern": "{id}.bin", "frame": "sensor", "units": "m",
              "layout": {"dtype": "float32", "shape": "(N,4)", "columns": ["x","y","z","reflectance"]}},
    "occ":  {"type": "labels", "pattern": "{id}.npz",
              "layout": {"key": "occ_label", "shape": "(200,200,16)", "spacing": [0.4,0.4,0.4]}}
  },
  "samples": [ {"id": "p01", "files": {"ct": "p01/ct", "mask": "p01/seg.nii.gz"}, "fields": {"patient": "p01"}} ],
  "size_mb": 120, "tags": ["medical"],
  "questions": []                           // non-empty = draft (see scanning-private-folders)
}
```

Role types: `volume`, `labels`, `mesh`, `points`, `image`, `transform`,
`splat`, `attribute`, `calibration`, `file`. Either list `samples`
explicitly (small bundled datasets and gated repos do) or give every role a
`pattern`: `{id}` names the sample; other placeholders (`{study}/{subject}`,
`images{split}/{id}`) become sample fields and, without `{id}`, join into the
sample id (`ds000001/sub-01`); a repeated placeholder (`{id}/anat/{id}_T1w.nii.gz`)
must match the same text; `*` matches within a path segment, `**` across.
Several DICOM files for one role collapse to their folder (fetched whole on
access); a folder entry from a listing (`.../series/`) is a DICOM series; a
second non-DICOM match is reported and the first kept. A `.mhd` header
brings its `.raw` / `.zraw` sibling along.

**Raw arrays need a layout.** A role whose files are `.npy`, `.npz`, `.bin`
or `.raw` must carry `layout`: `shape` (`"(N,4)"` for points, `"(L,W,H)"` for
a grid), `columns` naming `x`, `y`, `z` and the attributes, `dtype`
(required for headerless `.bin`), `key` for an `.npz`, optional `spacing` /
`origin` for grids and `scale` for colours. The manifest validator refuses
a non-draft manifest without it; the package never guesses a layout.

Sources:

| scheme | fields | behaviour |
|---|---|---|
| `local` | `root` (absolute, or relative to the manifest file) | files on disk |
| `https` | `files: {relpath: {sha512 or md5, url?, archive?, archive_root?, size_mb?}}`, `mirrors?` | download from `url` then hash-addressed mirrors, verify, cache under `~/.cache/pardesline/datasets/<name>/`; `archive: true` = the download is a tar/zip whose members land in the file's folder (or `archive_root`) |
| `hf` | `repo_id`, `revision="main"`, `repo_type="dataset"`, `paths` (sub-folders to list), `max_files=20000` | `huggingface_hub` listing per folder (cached per commit) and per-file download; the user's own token for gated repos |
| `archive` | `url` or `urls` (several archives forming one dataset), `format` zip/tar (inferred), `prefix`, optional `sha512`/`md5` (single url) | remote archives read by HTTP Range: index (zip central directory, incl. zip64; tar headers) cached on disk, each member fetched alone and CRC-checked (zip); whole download once when the server ignores ranges; compressed tars not supported; `fetch_folder` for DICOM series inside |
| `s3` | `bucket`, `endpoint` (default AWS), `prefix`, `max_files` | public bucket listing (ListObjectsV2) and plain HTTPS downloads; relative paths are the keys under `prefix` |
| `tcia` | `collection`, `modalities?`, `api` | NBIA REST API: `getSeries` listing cached on disk, `getImage` zip per series unpacked into a folder |
| `urllist` | `index_url`, `strip_prefix?`, `max_files` | a text file with one URL per line (MedShapeNet); relative path = file name |
| `open3d` | `dataset` (class name in `open3d.data`) | Open3D downloads its own demo data |

Licence tiers for public data: permissive (CC-BY, MIT, ODC-By) may be
mirrored; non-commercial (KITTI, KiTS23) loader only with `commercial: false`;
gated / DUA (ShapeNet, BraTS, TCIA restricted) `requires_agreement: true`,
user credentials. Never redistribute; put the upstream terms in `note` and
mark `TO CONFIRM` when not established.

## Writing and loading your own manifest

`Manifest.from_dict(...)`, `Manifest.load(path)`, `m.save(path)`,
`m.describe()`, `m.to_json()`. `pl.load("study.manifest.json")` opens it
(relative `local` roots resolve against the file);
`pl.load("hf://org/name", manifest="my.json")` binds one to a repo.
Validation errors raise `pl.ManifestError` with the field path. Cache:
`pl.cache_dir()`, `pl.set_cache_dir(path)`, env `PARDESLINE_CACHE`;
`huggingface_hub` keeps its own cache (`HF_HOME`).

<sub>Source: `skills/datasets-and-manifests/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-14.</sub>
