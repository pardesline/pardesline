---
title: Concepts — dataset, manifest, object, catalog
description: The four ideas behind pardesline: a dataset is a manifest plus a source; an object is a file with frame, units, labels, licence and provenance; the catalog validates every algorithm parameter; standardization is explicit, never guessed.
---

# Concepts

## Dataset

A `Dataset` is a manifest plus a source. `pl.load(name_or_uri)` returns one; nothing is downloaded until a sample's role is accessed. Samples are grouped by what the manifest says pairs files (patient, frame, folder); `ds.filter(split="Tr")`, `ds.take(n)`, `ds.sample(n, seed)`, `ds.split(by="patient")` never mix patients across splits. `ds[0]` or `ds["case_001"]` is a `Sample`; `sample.role_name` is an `Object`.

```python
ds = pl.load("totalsegmentator_ct")
s = ds.take(1)[0]
s.roles  # ['ct', 'liver', 'spleen', 'kidney_left', ...]  (118 roles)
s.liver  # LabelMap, fetched now (one 50 MB member out of a 23 GB zip)
ds.citation  # what the data owner asks you to cite
```

## Manifest

A JSON document (pydantic model `pardesline.Manifest`) that says everything the files cannot say by themselves:

| Field | What it holds | Example |
|---|---|---|
| `source` | scheme and location: `https` files with checksums, `hf` repo + paths, `archive` url(s) read by HTTP Range, `s3` bucket, `tcia` collection, `urllist` index, `open3d`, `local` | `{"scheme": "archive", "url": "https://.../Task04_Hippocampus.tar", "prefix": "Task04_Hippocampus"}` |
| `roles` | one entry per file kind in a sample: `type` (volume, labels, mesh, points, splat, image, transform, array), `pattern` with placeholders, `frame`, `units`, `labels`, `layout` for raw arrays, `modality` | `"mask": {"type": "labels", "pattern": "Task04_Hippocampus/labelsTr/{id}.nii.gz", "labels": {"1": "anterior", "2": "posterior"}}` |
| `license` | `spdx`, `commercial`, `redistribution`, `requires_agreement`, `note`, `source_url` | `{"spdx": "CC-BY-SA-4.0", "commercial": true, "redistribution": "allowed"}` |
| `citation`, `homepage`, `pairing`, `size_mb`, `tags` | provenance and discovery | |
| `samples` | explicit list when patterns cannot derive it | the four SimpleITK excerpts |
| `questions` | non-empty on a draft: what a human must confirm | `scan` output |

The 43 bundled manifests live in `src/pardesline/data/manifests/`; `pl.describe(name)` prints one; `pl.Manifest.load(path)` reads yours. A manifest never embeds data and never guesses: a `.bin` without a `layout`, a label map without `labels`, a mesh without `units` are questions, not defaults.

## Object

Every file becomes one of `PointCloud`, `Mesh`, `Volume`, `LabelMap`, `Transform`, `Image`, `RawArray` (subclasses of `pardesline.Object`), carrying:

- `frame` (axes convention: LPS, RAS, sensor, Y-up; the affine for volumes) and `units` (mm, m);
- `labels` for label maps and the layout for raw arrays;
- `license` and `provenance`: the dataset, sample and role it came from, then every step applied;
- conversions named after the job: `volume.segment()`, `mask.to_mesh(label)`, `volume.to_mesh(isovalue)`, `mesh.to_points()`, `points.to_mesh()`, `points.align(moving)`, `volume.align(moving)`, `clean()`, `decimate()`, `smooth()`, `downsample()`, `normals()`;
- the libraries themselves: `to_open3d()`, `to_pyvista()`, `to_sitk()`, `to_numpy()`;
- `save(path)` writes the file and a `.pardesline.json` sidecar; `load` of such a file reads the sidecar back.

Conversions are exact when they can be (a label boundary, a DICOM series to a volume) and say so when they are not (Poisson reconstruction is lossy and parametric; the sidecar records `depth` and `density_quantile`).

## Catalog

`pl.catalog()` is the typed list of 19 modules, 73 methods and 371 parameters (`src/pardesline/catalog/data/*.json`): name, type, default, range, options, description, and since 0.3 the **rationale** for each default and the data it was **validated on** (`_defaults.json`). `pl.run("module.method", file, **params)` validates before anything runs: unknown names, wrong types and out-of-range values raise `ParameterError` with the accepted list. `obj.run(...)` does the same and records the step. `pl.describe("module.method")` prints all of it.

Every method is a script under `pardesline.ops` with an `argparse` CLI (`python -m pardesline.ops.registration.ransac_icp_pipeline --input ... --moving ... --output ...`), kept byte-identical to the PardesLine platform so results match between the laptop and the hosted version.

## Standardization

What "standardized" means here, concretely:

- **Typed roles**: a file is a volume, a label map, a mesh, a point cloud, a splat, an image or a raw array, and the type decides the conversions and the algorithms.
- **Frame and units** are known before you compute: LPS millimetres for medical volumes (from the header), the sensor frame in metres for KITTI sweeps (from the manifest), Y-up metres for the bunny.
- **Labels** have names; **layouts** turn headerless arrays into point clouds.
- **Standard files on export**: PLY for points, meshes and splats; MetaImage for volumes and label maps; sidecars next to each; a manifest for the folder (`ds.export(folder)`).
- **Patient-level splits** (`ds.split(by="patient")`) and **licence** on every object.

What it does not do: resample to a common spacing, reorient to a canonical axis order, normalise intensities. Those are algorithm choices (see `pyvista_volume_processing`, `simpleitk_registration`) and the medical-volumes guide explains when to make them.

## Licence

`ds.license` / `obj.license` is a `License` with `spdx`, `commercial`, `redistribution`, `requires_agreement`, `note`. Gated sources (AbdomenAtlas, CT-RATE) need your own Hub token after accepting the terms; non-commercial sources are flagged; sources without a standard licence print a warning and the owner's terms. Nothing is mirrored by pardesline: every loader fetches from the owner.

## MCP

`pardesline mcp` serves the same datasets, objects and catalog as tools for AI agents, plus the twenty expert guides. See [MCP server](../agents/mcp.md).
