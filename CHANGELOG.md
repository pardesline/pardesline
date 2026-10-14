# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Hugging Face datasets, for real.** `pl.load("hf://org/name[/sub/folder]")`
  loads a bundled manifest or, for any other repo, lists the folder, drafts a
  manifest and asks what it cannot establish (licence from the Hub card, units,
  labels, array layouts) - the same four asking modes as a private folder.
  Listings go per folder (`source.paths`), are cached on disk per commit and
  capped (`source.max_files`), with a clear message instead of an HTTP 429.
- **Remote archives read by HTTP Range** (`source.scheme: "archive"`): zip
  (incl. zip64) and uncompressed tar on S3 / Zenodo are indexed for a few KB
  and read member by member; whole download with checksum when the server
  ignores ranges.
- **Raw arrays through a layout**: `.npy` / `.npz` / `.bin` roles declare
  `layout` (dtype, shape, columns, key, spacing); `pl.load("sweep.bin",
  layout=...)`, `RawArray.as_points()` / `as_volume()`; decoded once into
  PLY / MetaImage so the 73 algorithms run unchanged; wrong layouts fail loudly.
- **Nine manifests**: `msd_task02_heart`, `amos22`,
  `kitti_raw_2011_09_26_drive_0001`, `hf_openmind`, `hf_nsclc_radiomics`,
  `hf_objaverse_glb_shard`, `hf_3d_arena`, `hf_uniocc_carla_mini`,
  `hf_kitti360_gs_subset`, each checked against the live source.
- `Dataset.export(folder)`: a standard copy (PLY / MetaImage / NIfTI, one
  sidecar per file, a local manifest) of any dataset or subset.
- CLI: `pardesline datasets`, `describe <dataset>`, `fetch`, `export`.
- `https` files accept an upstream `md5` and an `archive_root`; pattern
  placeholders other than `{id}` join into the sample id and become fields
  (`ds.filter(split="Tr")`).

## [0.2.0a1] — 2026-10-10

First open-source release of the package. Licence: Apache-2.0.

### Added
- **Local execution** of the 73 algorithms that power the PardesLine platform
  (19 modules: point clouds, meshes, surface reconstruction, registration,
  deformable registration, segmentation, SDF, LiDAR, stereo, collision,
  PyVista analysis and volume processing, SimpleITK registration and
  segmentation). Every algorithm runs on your machine with
  `pl.run(module, method, input, **params)` or as a CLI module.
- **Typed catalog** (`pl.catalog`) generated from the platform's module
  manifests: 371 parameters with type, default, range, choices and
  description. Parameters are validated and coerced before a run.
- **`pl.Object`**: a local file wrapped with its kind (point cloud, mesh,
  volume, transform, image), its sidecar metadata (registration transforms)
  and the provenance of every run that produced it.
- **`pl.load(path)`** for local files; `obj.run(...)` and `obj.methods()`.
- **`pardesline` CLI**: `list`, `describe`, `run`, plus the cloud commands.
- `pardesline.medical`: the SimpleITK service (volume I/O, DICOM series,
  rigid / affine / B-spline / demons registration, segmentation).

- **Object model**: `PointCloud`, `Mesh`, `Volume`, `LabelMap`, `Transform`,
  `Image` with `frame` (axes, units, affine, source), `labels`, `license` and
  `provenance`; `with_frame` / `with_labels` / `with_license`; `save()` writes
  a `.pardesline.json` sidecar that `load()` reads back. Volume headers give
  LPS/mm and the affine; glTF is Y-up/m by specification; other formats stay
  unknown until declared - never guessed.
- **Conversions**: `Volume.segment()` -> `LabelMap`; `LabelMap.to_mesh(label)`
  exact isosurface in world coordinates (in-process, direction cosines
  applied); `Volume.to_mesh(isovalue)`; `Mesh.to_points()`; `PointCloud.to_mesh()`;
  `align()` and `clean()` on clouds and volumes.
- **Datasets**: manifest schema (source, licence, citation, roles, samples,
  questions); `Dataset` / `Sample` with lazy fetch, `split()` by group,
  `filter`, `take`, `sample`; sources `local`, `https` (SHA-512, mirrors,
  tar/zip archives, cache), `hf://` (`[hf]` extra) and Open3D demo data.
- **Bundled manifests**: `rire_brain`, `popi_lung_4dct`, `liver_tumor_patient01`,
  `visible_human_head_mri`, `open3d_bunny`, `open3d_armadillo`, `open3d_icp_demo`.
- **`pl.scan(folder)`** drafts a manifest for a private folder and lists its
  open questions; `pl.load(folder)` raises `NeedsConfirmation` until they are
  answered (in the call, in the saved draft, interactively, or `assume=True`).

- **Skills for AI agents** under `skills/` (eight Claude Code skills) with a
  plugin manifest, so `/plugin marketplace add pardesline/pardesline` teaches
  an agent the package; `tests/test_skills.py` keeps them consistent with the
  catalog, the datasets and the public API.

### Changed
- The proprietary cloud client 0.1.0 is now the `pardesline.cloud`
  subpackage, re-licensed under Apache-2.0. The top-level helpers
  (`pl.login`, `pl.upload`, `pl.share`, `pl.o3d`, ...) keep working.

### Not yet in this release
- Manifests for the large public hubs (OpenMind, MSD, Objaverse, KITTI).
- Splats as a first-class kind.
- The local MCP server.

[Unreleased]: https://github.com/pardesline/pardesline/compare/v0.2.0a1...HEAD
[0.2.0a1]: https://github.com/pardesline/pardesline/releases/tag/v0.2.0a1
