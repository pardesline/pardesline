# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.3.0](https://github.com/pardesline/pardesline/compare/v0.2.0...v0.3.0) � 2026-10-17

The "reference repository" release: a documentation site, every default documented with its reason, thirteen executed examples, benchmarks, a contributor funnel and release automation. The package API is unchanged; two bugs found on the way are fixed.

### Added
- `examples/`: thirteen runnable examples, one folder each, titled "<algorithm or model> on <dataset>", with the images and numbers they produce and a README per example; `examples/real_cases/` for industrial data that cannot be redistributed.
- Remote archives up to 64 MB (`PARDESLINE_WHOLE_ARCHIVE_MB`) are downloaded once and indexed locally instead of one Range request per member: the first `pl.load("msd_task04_hippocampus")` goes from 194 s to a few seconds.
- Documentation site at https://pardesline.github.io/pardesline/ (MkDocs Material, versioned with `mike`): one page per dataset (43) and per algorithm family (19) generated from the manifests and the catalog, model pages, the twenty skills as guides, 18 how-to pages titled as the questions people search for, "Why our defaults work", comparison with Open3D / PyVista / SimpleITK / trimesh / MONAI / TorchIO / Hugging Face datasets, FAQ, API reference from the docstrings, `llms.txt` and `llms-full.txt`.
- `docs/_gen/datasets_table.py` generates the README dataset table from the manifests; the generated pages carry the date of the source's last commit.
- Every catalog parameter carries `rationale` (why the default, when to change it) and every method `validated_on` (`src/pardesline/catalog/data/_defaults.json`); `pl.describe()` prints them; `tests/test_catalog.py` enforces full coverage.
- `benchmarks/`: package defaults vs upstream defaults on the Stanford bunny (registration, Poisson reconstruction), tables generated into `benchmarks/results.md`.
- `tests/test_docs_snippets.py` executes the code blocks of the README, the tutorial and the how-to pages (network marker).
- Docstrings on every public function and class (31 added).
- CI: type-check job (mypy), coverage uploaded to Codecov, native matrix on Python 3.10 and 3.13, a job that executes the README demo and the documented code blocks against the live datasets, a nightly workflow that installs from PyPI on three OSes and runs the demo, OpenSSF Scorecard, Dependabot (GitHub Actions only), pre-commit config, `.zenodo.json` for a DOI per release, `docs/assets/make_social_preview.py`.
- Release automation: Release Please opens the release pull request from the conventional commits (version bump in `_version.py`, `CITATION.cff` and the two plugin manifests, CHANGELOG section); merging it creates the tag and the GitHub release, then dispatches the PyPI upload (Trusted Publishing) and the versioned documentation.
- Contributor funnel: issue forms (bug, feature, dataset request, algorithm or model request, real case), pull request template, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `CODEOWNERS`, `.all-contributorsrc`, `templates/new_dataset`, `templates/new_algorithm`, `templates/new_model`, `templates/new_pipeline` with tests, `docs/seo/issues-to-create.md` (tracking issues, 16 good first issues, 11 help wanted) and `docs/seo/apply_github.py` to apply labels, metadata and issues through the API.
- `docs/showcase/`: the ten pipeline posters with, for each, the snippet, the expert skill and the MCP tool; `posters.gif` (carousel), `mosaic.jpg`, `social-preview.png` for the repository card; `CITATION.cff`.

### Changed
- README rewritten as a front page: poster carousel, the promise in three lines, install, an executed 30-second demo (CT/MR registration on RIRE), generated datasets table, algorithms and models tables, "Defaults that work on real data" side by side with the tutorial defaults, comparison table, gallery, MCP, roadmap (model registry first), community, citation.
- `[local]` accepts Open3D 0.20, which ships Python 3.13 wheels: `pip install "pardesline[all]"` now works on 3.10-3.13 (the native test suite passes on 3.13 with 0.20).
- PyPI metadata: description, 26 keywords, classifiers and project URLs unified on the documentation site.

### Fixed
- `.nii.gz` files are accepted by every module that accepts `.nii` (`Volume.segment()` on a Decathlon volume raised "does not accept '.gz' files").
- Archive members whose names would escape the dataset cache (`../evil.bin`) are ignored at index time and refused by `fetch`.
- Docs deployment: mike aliases are copies instead of symbolic links, which the GitHub Pages builder rejects; the old hand-written `docs/index.html` landing page is removed now that Pages serves the `gh-pages` branch.

## [0.2.0] — 2026-10-14

First stable release of the open package: everything below is on top of 0.2.0a1.

### Added
- **Eleven expert skills with reference scripts**, served by the MCP server
  (`list_skills`, `get_skill`, `pardesline://skill/{name}`) and shipped in the
  wheel: 3-D representations, point-cloud registration (RANSAC + FPFH + ICP,
  CPD), multimodal rigid registration (SimpleITK Mattes MI), atlas label
  transfer, PointNet segmentation, DINOv3 dense features (Gram anchoring,
  frozen backbone + Faster R-CNN), JEPA pretraining (3-D ViT reference),
  VAE anomaly detection, Gaussian splatting (points -> 3DGS PLY), medical
  segmentation models (nnU-Net export) and 3-D evaluation metrics. The
  NumPy / Open3D / SimpleITK scripts run on the bundled datasets; the PyTorch
  ones are reference implementations.
- **Local MCP server** (`pardesline mcp`, extra `[mcp]`): twelve tools
  (datasets, samples, scan / confirm, export, catalog, run, describe_object,
  to_mesh), three resources and a `start_here` prompt over stdio or
  streamable HTTP, for Claude, Gemini, Cursor, Codex and any MCP client,
  without an account. Questions come back as JSON for the agent to relay; the
  repo ships a `.mcp.json` and the plugin declares the server. New skill
  `mcp-server`.
- **Medical 3D datasets, one line each.** 27 new manifests: the ten Medical
  Segmentation Decathlon tasks, TotalSegmentator CT (117 structures) and MRI
  (56), LUNA16, IXI, VerSe 2019, SPIDER, CHAOS (DICOM), four TCIA collections
  (Pancreas-CT, LIDC-IDRI, NSCLC-Radiomics, Prostate-3T), OpenNeuro ds000228,
  KiTS23, AbdomenAtlas Mini and CT-RATE (gated), the BiomedSegFM 3-D
  validation set, MedShapeNet (106 101 STL shapes) and the C3VD endoscopy
  Gaussian splats - 43 manifests in all, each listed and sampled live.
- New sources: `s3` (public bucket, ListObjectsV2, `pl.load("s3://...")`),
  `tcia` (NBIA REST API, one DICOM series per entry,
  `pl.load("tcia://Collection/CT")`), `urllist` (a text index of URLs);
  `archive` sources may span several archives (`urls`).
- DICOM series as folder entries (fetched whole), MetaImage `.raw` siblings
  fetched with their header, repeated pattern placeholders
  (`{id}/anat/{id}_T1w.nii.gz`) matched as backreferences.
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

[0.3.0]: https://github.com/pardesline/pardesline/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pardesline/pardesline/compare/v0.2.0a1...v0.2.0
[0.2.0a1]: https://github.com/pardesline/pardesline/releases/tag/v0.2.0a1
