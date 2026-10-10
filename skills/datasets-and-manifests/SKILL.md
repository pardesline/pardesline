---
name: datasets-and-manifests
description: >-
  Load datasets with pardesline by manifest instead of per-dataset code:
  `pl.load("rire_brain")` and the other bundled datasets (POPI 4D-CT, liver tumour
  segmentations, Visible Human MRI, Open3D bunny/armadillo/ICP pairs), the Dataset /
  Sample API (roles as attributes, lazy fetch, `take`, `sample`, `filter`, leakage-free
  `split`, `volumes`/`meshes`/`points`, `fetch_all`), the manifest JSON schema (source
  local/https/hf/open3d, licence tiers, citation, roles with frame/units/labels/layout,
  explicit samples or patterns), `pl.load("hf://org/name")`, the download cache and
  SHA-512 verification. Use when the user asks for sample data, a public dataset, a
  Hugging Face 3D dataset, or how to write a manifest for one.
---

# Datasets and manifests

`pl.load` never knows a dataset; it knows a **manifest**. A manifest says
where the files come from (with checksums), under which terms, how files
group into samples, and what the files cannot say by themselves (frame,
units, label meanings, array layout). Same code path for a bundled public
dataset, a Hugging Face repo and a private folder.

## Bundled datasets (`pl.datasets()`, `pl.describe(name)`)

| Name | Content | Roles | Size |
|---|---|---|---|
| `rire_brain` | RIRE training_001: CT + MR-T1 of one brain (SimpleITK notebooks excerpt) | `ct`, `mr_t1` (volume) | 19 MB |
| `popi_lung_4dct` | POPI-model thorax 4D-CT, phases 00..50 (`phase_00` ... `phase_50`), air/body/lungs mask on phase 00 | `ct` (volume), `mask` (labels `{1: body, 2: lungs}`) | 500 MB |
| `liver_tumor_patient01` | abdominal CT + three radiologists' tumour segmentations | `ct` (volume), `rad01` `rad02` `rad03` (labels `{1: tumor}`) | 2 MB |
| `visible_human_head_mri` | NLM Visible Human head MRI | `mri` | 2 MB |
| `open3d_bunny`, `open3d_armadillo` | Stanford meshes via `open3d.data` | `mesh` | 3 / 7 MB |
| `open3d_icp_demo` | Redwood indoor fragments, pairs `pair_0_1`, `pair_1_2` | `source`, `target` (points, sensor frame, m) | 6 MB |

All licence notes say **TO CONFIRM**: the terms were not established by the
package authors. Say so when the user plans redistribution or commercial use.
Medical ones need `[medical]`, Open3D ones need `[local]`.

```python
ds = pl.load("popi_lung_4dct")
ds.describe()  # licence, citation, roles, sample count, cache location
len(ds)
ds.ids  # 6, ['phase_00', ...]
s = ds["phase_00"]  # or ds[0]
s.roles, s.fields  # ['ct', 'mask'], {'patient': 'popi_01', 'phase': '00'}
ct = s.ct  # Volume, fetched + SHA-512 verified on first access, cached
mask = s.mask  # LabelMap with labels from the manifest
mask.frame.describe()  # "LPS, mm (file)"
lungs = mask.to_mesh(label=2)
moved = s.ct.align(ds["phase_50"].ct, num_iterations=100)
ds.license.describe()
ds.citation
```

## Dataset API

- Indexing: `ds[i]`, `ds["sample_id"]`, iteration, `len`, `ds.ids`.
- Subsets (lazy, same source): `ds.take(n)`, `ds.sample(n, seed=0)`,
  `ds.filter(phase="00")` on sample fields.
- `ds.split(by=None, fractions=(0.8, 0.2), seed=0)` -> tuple of Datasets;
  every sample sharing the `by` field (default: the manifest `pairing` key,
  e.g. `patient`) lands in one part, so no patient straddles train/test.
- By role or type: `ds.role("ct")` (iterator of Objects), `ds.volumes`,
  `ds.meshes`, `ds.points` (iterators across samples), `ds.roles` (manifest
  roles), `ds.manifest`.
- `ds.fetch_all()` downloads everything now and returns the file count.
- Sample: `s.get("ct")`, `s["ct"]`, `s.ct` (cached), `s.path("ct")` (local
  path after fetch), `s.id`, `s.fields`, `s.license`, `s.describe()`.

Objects from a dataset carry `role`, the dataset licence, the role's frame
(`source="manifest"`, never overriding a header), `labels`, `meta["modality"]`
/ `meta["layout"]`, and a first provenance step `{"step": "load", "dataset",
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
  "pairing": "patient",                     // what groups files into a sample
  "roles": {
    "ct":   {"type": "volume", "pattern": "{id}/ct/*.dcm", "frame": "LPS", "units": "mm", "modality": "CT"},
    "mask": {"type": "labels", "pattern": "{id}/seg.nii.gz", "labels": {"1": "left_atrium"}},
    "mesh": {"type": "mesh",   "pattern": "{id}/la.stl", "units": "mm", "frame": "LPS"},
    "lidar": {"type": "points", "pattern": "{id}.bin",
              "layout": {"dtype": "float32", "shape": "(N,4)", "columns": ["x","y","z","reflectance"]}}
  },
  "samples": [ {"id": "p01", "files": {"ct": "p01/ct", "mask": "p01/seg.nii.gz"}, "fields": {"patient": "p01"}} ],
  "size_mb": 120, "tags": ["medical"],
  "questions": []                           // non-empty = draft (see scanning-private-folders)
}
```

Role types: `volume`, `labels`, `mesh`, `points`, `image`, `transform`,
`splat`, `attribute`, `calibration`, `file`. Either list `samples`
explicitly (bundled manifests do) or give every role a `pattern` with
`{id}` (and other `{field}` placeholders, `*` within a segment, `**` across);
samples are then derived from the source listing and several matches for one
role (DICOM slices) collapse to their folder.

Sources:

| scheme | fields | behaviour |
|---|---|---|
| `local` | `root` (absolute, or relative to the manifest file) | files on disk |
| `https` | `files: {relpath: {sha512, url?, archive?, size_mb?}}`, `mirrors?` | download from `url` then hash-addressed mirrors (`{sha512}` placeholder; defaults are the SimpleITK S3 and Kitware Girder stores), verify SHA-512, cache under `~/.cache/pardesline/datasets/<name>/`; `archive: true` means the download is a tar/zip whose members land in the declared file's folder (MetaImage `.mhd` + `.raw`) |
| `hf` | `repo_id`, `revision="main"`, `repo_type="dataset"` | `huggingface_hub` per-file download and listing; gated/private repos use the user's own token (`huggingface-cli login` or `HF_TOKEN`), the package never scripts past a click-through |
| `open3d` | `dataset` (class name in `open3d.data`) | Open3D downloads its own demo data |

Licence tiers for public data: permissive (CC-BY, MIT, ODC-By) may be
mirrored; non-commercial (KITTI, KiTS23) loader only with `commercial: false`;
gated / DUA (ShapeNet, BraTS, TCIA restricted) `requires_agreement: true`,
user credentials. Never redistribute; put the upstream terms in `note` and
mark `TO CONFIRM` when not established.

## `hf://`

`pl.load("hf://org/name")` needs a manifest for that repo: a bundled one, or
`pl.load("hf://org/name", manifest="my.json")`. `.npy` / `.npz` / `.bin`
roles **must** carry `layout` (dtype, shape, columns); the package refuses to
guess an array layout. Listing and fetching go through `huggingface_hub`
(`pip install "pardesline[hf]"`).

## Writing and loading your own manifest

`Manifest.from_dict(...)`, `Manifest.load(path)`, `m.save(path)`,
`m.describe()`, `m.to_json()`. `pl.load("study.manifest.json")` opens it
(relative `local` roots resolve against the file). Validation errors raise
`pl.ManifestError` with the field path. Cache: `pl.cache_dir()`,
`pl.set_cache_dir(path)`, env `PARDESLINE_CACHE`.
