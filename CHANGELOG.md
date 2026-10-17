# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.3.0](https://github.com/pardesline/pardesline/compare/v0.2.0...v0.3.0) (2026-10-17)


### Fixed

* **docs:** copy aliases for Pages, drop old landing page, no pip bump PRs ([aa996b9](https://github.com/pardesline/pardesline/commit/aa996b91f2278247d489c1d5ec22e79602a22e47))
* **release:** bump _version.py and CITATION.cff through release-please ([ce80de9](https://github.com/pardesline/pardesline/commit/ce80de9e25ff2905e4a2cffc8c5e9c9a37925baa))


### Documentation

* carousel below the title at 560 px, posters ordered JEPA, DINOv3, echo, splats, representations, atlas, PointNet, VAE, CT/MR, ICP ([eea9723](https://github.com/pardesline/pardesline/commit/eea97237111a531925b81a04784f7417c6cfe492))
* contributor funnel - issue forms, templates, support, issues to create ([5fbbc04](https://github.com/pardesline/pardesline/commit/5fbbc04dbdf13b6aea3b1deebff1b015d440df21))
* documentation site, documented defaults, benchmarks, docstrings ([6e5e057](https://github.com/pardesline/pardesline/commit/6e5e057f35578efacde0fc62c3dd4eaee93f084d))
* front-page README with poster carousel, docs pages, Pages landing, CITATION.cff ([55e7d74](https://github.com/pardesline/pardesline/commit/55e7d74481fbc72d9e6e34c726780b6d0a165c53))
* launch kit, content calendar, final report ([44920e9](https://github.com/pardesline/pardesline/commit/44920e9ce5da9d6d5b9a2ada6605681e8c843a90))
* README as a landing page, twelve runnable examples, small-archive fast path ([336fa2d](https://github.com/pardesline/pardesline/commit/336fa2d0bda987142ae05f14e2875e60140676e7))
* relative image paths in the README (absolute raw URLs do not render on a private repository) ([97c8c33](https://github.com/pardesline/pardesline/commit/97c8c337e92b7ba3c61d8354595eb61f9d6f048d))
* SEO foundation - keyword map, GitHub metadata, PyPI metadata ([fe4cd1f](https://github.com/pardesline/pardesline/commit/fe4cd1fe62200f97d83d59b984b44f32322380f4))
* showcase of the ten pipelines; ci: pin ruff 0.17 ([fa53d61](https://github.com/pardesline/pardesline/commit/fa53d6125f83821dbd1ce383fa78d8b36541dd01))
* stamp generated pages with the source's last commit date ([0642797](https://github.com/pardesline/pardesline/commit/06427978e26c9471ff9081999254e2e5c5ad56bd))


### Infrastructure

* scorecard-action 2.4.4, docs default version, branch protection option ([1b50ee7](https://github.com/pardesline/pardesline/commit/1b50ee7ec7cdfb36d779cc9d75f51894f15cff5d))

## [Unreleased]

### Added
- `examples/`: twelve runnable examples, one folder each, titled "<algorithm or model> on <dataset>", with the images they produce.
- Remote archives up to 64 MB (`PARDESLINE_WHOLE_ARCHIVE_MB`) are downloaded once and indexed locally instead of one Range request per member: the first `pl.load("msd_task04_hippocampus")` goes from 194 s to a few seconds.
- `docs/_gen/datasets_table.py` generates the README dataset table from the manifests.
- Documentation site (MkDocs Material, `mkdocs.yml`, `.github/workflows/docs.yml` with `mike` versioning): one page per dataset (43) and per algorithm family (19) generated from the manifests and the catalog, model pages, the twenty skills as guides, 18 how-to pages titled as the questions people search for, "Why our defaults work", comparison, FAQ, API reference from the docstrings, `llms.txt`.
- Every catalog parameter now carries `rationale` (why the default, when to change it) and every method `validated_on` (`src/pardesline/catalog/data/_defaults.json`); `pl.describe()` prints them; `tests/test_catalog.py` enforces full coverage.
- `benchmarks/`: package defaults vs upstream defaults on the Stanford bunny (registration, Poisson reconstruction), tables generated into `benchmarks/results.md`.
- `tests/test_docs_snippets.py` executes the code blocks of the README, the tutorial and the how-to pages (network marker).
- Docstrings on every public function and class (31 added).
- CI: type-check job (mypy), coverage uploaded to Codecov, native matrix on Python 3.10 and 3.13, a job that executes the README demo and the documented code blocks against the live datasets, a nightly workflow that installs from PyPI on three OSes and runs the demo, OpenSSF Scorecard, Dependabot, pre-commit config, release-please (version bump in `_version.py`, the plugin manifests and `CITATION.cff`, CHANGELOG section, tag and GitHub release), `.zenodo.json` for a DOI per release, `docs/assets/make_social_preview.py`.
- Contributor funnel: issue forms (bug, feature, dataset request, algorithm or model request, real case), pull request template, `SUPPORT.md`, `CODEOWNERS`, `.all-contributorsrc`, `templates/new_dataset`, `templates/new_algorithm`, `templates/new_model`, `templates/new_pipeline` with tests, a README per example, `docs/seo/issues-to-create.md` (tracking issues, 16 good first issues, 11 help wanted) and `docs/seo/apply_github.py` to apply labels, metadata and issues through the API.

### Changed
- `[local]` accepts Open3D 0.20, which ships Python 3.13 wheels: `pip install "pardesline[all]"` now works on 3.10-3.13 (the native test suite passes on 3.13 with 0.20).
- PyPI metadata: description, 26 keywords, classifiers and project URLs unified on the documentation site.

### Fixed
- Docs deployment: mike aliases are copies instead of symbolic links, which the GitHub Pages builder rejects; the old hand-written `docs/index.html` landing page is removed now that Pages serves the `gh-pages` branch.
- Archive members whose names would escape the dataset cache (`../evil.bin`) are ignored at index time and refused by `fetch`.
- `.nii.gz` files are accepted by every module that accepts `.nii` (`Volume.segment()` on a Decathlon volume raised "does not accept '.gz' files").

### Changed
- README rewritten as a short front page: animated poster carousel, the
  promise in three lines, install, a 30-second example, a Mermaid diagram of
  how the pieces fit, the showcase, the MCP tools. The detailed sections moved
  to `docs/datasets.md`, `docs/catalog.md`, `docs/running-modes.md`,
  `docs/mcp.md` (text unchanged).

### Added
- `docs/showcase/`: the ten pipeline posters with, for each, the snippet, the
  expert skill and the MCP tool; `posters.gif` (carousel), `mosaic.jpg`,
  `social-preview.png` for the repository card; `docs/index.html`, a landing
  page with a real carousel for GitHub Pages; `CITATION.cff`.

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

[Unreleased]: https://github.com/pardesline/pardesline/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pardesline/pardesline/compare/v0.2.0a1...v0.2.0
[0.2.0a1]: https://github.com/pardesline/pardesline/releases/tag/v0.2.0a1
