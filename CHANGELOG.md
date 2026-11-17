# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.6.0](https://github.com/pardesline/pardesline/compare/v0.5.0...v0.6.0) (2026-11-17)


### ⚠ BREAKING CHANGES

* code that used pardesline.cloud, pl.login, pl.upload, pl.share or the cloud CLI commands must pin pardesline<0.6.

### Added

* MCP tool metadata, glama.json and the Claude plugin directory edition ([2f2825a](https://github.com/pardesline/pardesline/commit/2f2825a9a28d45746ddb31fe9f98f181c6d66e9e))
* **mcp:** tool titles, annotations and parameter descriptions; serverInfo reports the package version ([62ae7fc](https://github.com/pardesline/pardesline/commit/62ae7fc1e9180a5f3c879fadddc4cb3924d3b40a))
* **plugin:** Claude plugin directory edition in plugins/pardesline ([cb1cb42](https://github.com/pardesline/pardesline/commit/cb1cb425485d642f07dfb0ed71d4f0bbbe148b16))
* the open-source package is independent of the PardesLine platform ([4fe5667](https://github.com/pardesline/pardesline/commit/4fe566718ddf82e9e9db488a6dcaf251b71367b0))


### Fixed

* **plugin:** directory edition - quoted frontmatter, no cloud client ([26a1d17](https://github.com/pardesline/pardesline/commit/26a1d17cc969981ed9ee805dfbeafadb5c1495c3))
* **plugin:** double-quoted skill frontmatter in the directory edition ([5b2410d](https://github.com/pardesline/pardesline/commit/5b2410dd6581798d007314299d16f08045b55bbf))
* **plugin:** leave the cloud client out of the directory edition ([827406d](https://github.com/pardesline/pardesline/commit/827406dd5ab651fbc9228c16b5b908f38d83a92b))
* **privacy:** pl.o3d / pl.pv / pl.sitk never call the platform for a user who is not signed in ([074657a](https://github.com/pardesline/pardesline/commit/074657acf292874a1d617f18050eb8834b79507f))

## [0.5.0](https://github.com/pardesline/pardesline/compare/v0.4.0...v0.5.0) (2026-11-16)

The core release: what `save` writes, what a registration tells its caller, which licence a result
carries and how label volumes are read, fixed after a downstream review of 0.3.1, plus the second
batch of the 2026-11-15 audit. 0.4.0 was already published, so these changes form 0.5.0: several
calls now raise where they returned, which before 1.0 is a minor version.

### Fixed: results that change
- Default rigid and affine volume registration use regular-step gradient descent, 300 iterations
  and 10 % sampling: a sphere shifted by 2 mm had "registered" 7.5 m away with exit code 0, and
  rotated blobs ended 5-9 mm off; now 0.01-0.76 mm on the same synthetic pairs.
- `Object.save` converts when the extension changes (or raises): `save("x.stl")` on a PLY mesh wrote
  PLY bytes; a DICOM folder or a raw array saved under another extension, and `x.mhd` saved as
  `y.mhd` (header still pointing at `x.raw`), are fixed too.
- The frame of an operation's output says `derived` (it said `file`) and carries the affine of the
  output grid.
- A result made from several inputs carries the most restrictive licence (a commercial fixed input
  plus a non-commercial moving input gave a "commercial use allowed" result); unknown stays unknown.
- A saved non-commercial object keeps `commercial: false` (it reloaded as unknown).
- Label maps keep their stored pixel type: label ids above 2^24 are exact.
- `poisson` no longer trims 1 % of the vertices by default (the trimming opened closed surfaces).
- Lengths in file units accept millimetre values in `pl.run` (twenty catalog bounds sized for
  unit-scale data refused them).

### Changed defaults
- `simpleitk_registration` rigid / affine: `num_iterations` 100 -> 300, `sampling_percentage`
  0.01 -> 0.1, new `optimizer` `regular_step` (was plain gradient descent); advanced_rigid's
  refinement uses `regular_step` too.
- `point_cloud_reconstruction.poisson` `density_quantile` 0.01 -> 0.
- `pyvista_analysis.pv_glyph` `scale_factor` 0.01 -> 0 (= 5 % of the largest extent).
- `sdf.sdf_voxel_visualization` `min_clamp` / `max_clamp` -0.1 / 0.1 -> minus / plus one grid step.

### New parameters
- `min_fitness` (0.5) on `registration` ransac_global, icp_refinement, ransac_icp_pipeline and
  `deformable_registration.cpd_deformable`; `min_overlap` (0.25) and `min_similarity` (0.05) on
  `simpleitk_registration` rigid, advanced_rigid, affine, bspline, demons.
- `optimizer` on rigid, advanced_rigid, affine; `bspline_metric` on bspline; `auto_retry` on
  `point_cloud_reconstruction.alpha_shape`.
- Python API: `load_volume(path, pixel_type=None)`, `resample(..., interpolator=)`,
  `Volume.resample()` / `LabelMap.resample()` (nearest for label maps), `register_*(...,
  quality={})`, `registration_quality()`, `check_registration_quality()`,
  `object.frame.combine_licenses()` and `LICENSE_ORDER`, `Object.quality`,
  `convert.save_as()` and `SAVE_WRITERS`, manifest `source.pins`, `data.pinning.pin_status()`.

### New result fields
- Registration sidecars: `quality` with `status` (`ok`, `below_floor`, `ambiguous`), `fitness`,
  `inlier_rmse`, `fitness_threshold` (point clouds) or `overlap`, `similarity` (volumes),
  `final_metric`, `metric_name`, `stop_condition`, `iterations`, `floors`. `cpd_deformable` now
  writes a sidecar; `alpha_shape` writes one with the alpha used.
- MCP `run_method`: `license`, `license_text`, `frame`, `quality`, `object_sidecar`; it writes
  `<output>.pardesline.json`.
- Provenance of `resample`: the interpolator used.

### Behaviours that are now errors
- A registration below its quality floor writes its output and JSON, then exits with code 4
  (`RunError` "the registration quality is below the floor").
- Saving to an extension with no writer for the content raises `ValueError` (for example a mesh
  to `.pcd`, a point cloud to `.stl`, anything to `.glb`: Open3D 0.19 writes GLB files that
  other readers reject).
- `pv_threshold_volume` needs `--lower` and `--upper`; `pv_scalar_stats` without point data needs
  `--scalars elevation`; `alpha_shape` with an alpha that gives an empty mesh exits 1 unless
  `auto_retry`; `sdf_voxel_visualization --resolution` outside 8-128 exits 1 (it was clamped);
  dense SDF / occupancy / erosion grids above 50 million nodes exit 1 with the voxel size to use;
  an archive whose size or ETag differs from its manifest pin is refused.
- `resample(interpolator=...)` with an unknown name raises `ValueError`.

### Known limitation
- macOS: seeded Open3D RANSAC (`ransac_global`, the RANSAC stage of the pipeline and of
  `icp_refinement`, RANSAC plane fits) is not repeatable run to run, although it is on Linux and
  Windows: macOS CI of 0.4.0 gave different coarse poses for the same seed even with
  OMP_NUM_THREADS=1. The pipeline's ICP refinement converged to the same pose there. Seeded
  SimpleITK registrations agree to about 1e-4 mm on every platform (multithreaded sums).

### Also
- Child processes of the runner get `stdin=DEVNULL` (they inherited the MCP server's protocol stream).
- SDF, occupancy, erosion and collision warn when the input mesh is not watertight.
- Manifests say exactly which data they load: the 10 Hugging Face manifests are pinned to the
  commit read on 2026-11-15 (they followed the moving `main`), the 20 archive manifests record the
  size (and ETag when the server sends one) of every archive URL, and an archive that changed is
  refused. Six sources that the format cannot pin yet (one S3 bucket, four TCIA collections, one
  URL list) are listed with their reason; `tests/test_manifest_pinning.py` fails on any other.
- AMOS22 licence: the Zenodo record states CC-BY-4.0, the archive's `dataset.json` CC-BY-SA 4.0;
  the more restrictive, CC-BY-SA-4.0, stays recorded, with both statements and the date read.
- Texts: voxelization outputs surface voxels; Taubin smoothing is low-shrinkage, not
  volume-preserving; a false comment on multi-scale ICP is gone.
- The runner's exit-code lookup is typed (the mypy job of CI failed after the merge).

## [0.4.0](https://github.com/pardesline/pardesline/compare/v0.3.1...v0.4.0) — 2026-11-15

The correctness release. A correctness audit of 2026-11-15 ran the algorithm scripts unchanged on
synthetic data with known answers and found results that were wrong without any error. This
release fixes the 48 bugs it listed that exist in this package, and 10 more found while fixing them
([additional findings](https://pardesline.github.io/pardesline/latest/audit/2026-11-additional-findings/)).
Every fix has a regression test that fails on 0.3.1 (`tests/test_regressions_*.py`, synthetic data,
fixed seeds, no download). **Numerical results change** for the algorithms listed below, and several
calls that used to "succeed" on meaningless defaults now stop with an error: read the three lists
after the fixes before upgrading a pipeline.

### Fixed: results that change

Medical registration (`simpleitk_registration`, `pardesline.medical`)
- `advanced_rigid`: the search and refinement transforms were composed in the wrong order
  (O(M(p)) instead of M(O(p))); the rotation search sampled 5 % of the voxels at random at shrink 8
  and picked wrong poses in 3 runs out of 4: it now uses every voxel of the coarse level.
- `bspline`: the optimised control grid is the one `grid_spacing` asks for. It was about 4 times
  coarser (the multi-level refinement never ran); the method now uses a 4-2-1 image pyramid.
- `rigid`, `affine`, `advanced_rigid`, `bspline`: the random metric sampling is seeded; two runs on
  the same input give the same transform (they differed by up to 0.09 rad).
- Registration results are flat composite transforms: `save_transform(t, "x.h5")` works for every
  method (it raised for advanced rigid and B-spline).
- `demons` (JSON sidecar): `mean_displacement_mm` and `std_displacement_mm` are statistics of the
  displacement length (the mean averaged signed x, y, z components and could be 0 for a 4 mm field).
- `difference_analysis`: `high_diff_voxels` counts every difference above `lower_threshold`
  (differences above 400 were left out).

Medical segmentation (`simpleitk_segmentation`)
- `otsu_threshold`, `connected_components`, `watershed`: voxels brighter than 255 are no longer
  dropped (bone and contrast in CT).
- `watershed`: returns the objects (it returned an empty label map); `seed_radius` is in mm as
  documented (it was in voxels); objects cut by the image border are removed; a separate object too
  thin for its own seed stays unlabelled instead of taking a neighbour's label.

Volume input and output
- `.vti` files are written and read with their direction matrix (oblique volumes were saved
  axis-aligned: 11.9 mm off at 30 degrees).
- `load_volume("x.vti")` reads `x.vti`; a sibling `x.mha` is no longer substituted.
- DICOM folders whose files form no series are stacked by slice position (Image Position Patient
  along the slice normal), not by file name.

Point-cloud registration (`registration`)
- `ransac_global`, `icp_refinement`, `ransac_icp_pipeline`: a `voxel_size` you give is used as given
  (values outside 0.5-5 % of the diagonal were replaced by 1.3 %).
- RANSAC is seeded and reproducible (Open3D's RANSAC threads share one random generator, so the
  scripts run Open3D on one thread). `ransac_global` and the pipeline run 8 seeds and keep the pose
  with the best threshold-free distance score; the pipeline also tests the 90/180/270-degree
  symmetric poses and reports an ambiguous result. On a near-symmetric part, one seed was 91 to 180
  degrees off in 3 to 6 runs out of 6; the pipeline now lands within 0.3 degree.
- The pipeline refines in two ICP passes (1.5 then 0.4 voxel) with 100 iterations; one pass at 0.4
  voxel stalled from RANSAC-sized errors in 18 of 20 starts.
- The point-to-point fallback uses your convergence settings; when ICP finds nothing the RANSAC pose
  is kept and labelled as such.
- Outputs are the moving cloud as read (colours, normals, point order) transformed by T; they were
  painted yellow with re-estimated normals.

Deformable point clouds (`deformable_registration`)
- `cpd_deformable`: `tolerance` reaches pycpd (it was passed under a name pycpd ignores); the
  normalisation scale no longer grows with the point count; `beta` defaults to 2 (with 100 the
  registration was worse than none: 1.11 -> 1.34 mm; now about 0.2 mm on the same case).
- `gaussian_deformation`: the field falls continuously to 0 at the radius (it jumped from 13.5 % of
  the displacement to 0 there).

Point-cloud processing
- `ransac_plane`: the output keeps the input point order (inliers were moved first); plane equation
  and inlier indices are written to the JSON sidecar; the plane fit is seeded. `ground_removal` and
  `object_clustering` seed their plane fit too.
- `pv_random_sample`: seeded by default; with `replace=true` the duplicates are written (the output
  had fewer points than reported).

Meshes, distance fields and collision
- `compute_sdf` (and `occupancy_reconstruction`, `binary_erosion`): output faces point outward (the
  SDF mesh was inside-out); no zero-area or duplicate faces by default.
- Signed distances and occupancy decide inside / outside by a majority of 3 rays (`sign_rays`); one
  ray counted a point 6.8 mm outside a sphere as inside.
- `penetration_depth`, `sdf_collision`: the obstacle is placed against the surface actually met along
  +x (it missed every non-spherical part, e.g. a cube); surface sampling is seeded; in
  `sdf_collision` penetrating points are at the red end of the colormap (they were blue).
- `poisson`, `ball_pivoting`: normals of a cloud without normals use a radius of 3 x the point spacing
  (an absolute 0.1 gave inside-out, open surfaces on data in mm); the signed volume is logged.
- `mesh_to_pcd_uniform`, `mesh_to_pcd_poisson_disk`: the seed is honoured (it was silently dropped).
- `pv_contour`: surfaces of oblique volumes are in the right place (12.4 mm off at 25 degrees).
- `pv_slice`, `pv_slice_orthogonal`: a coordinate of 0 is 0 (it meant "centre").
- `detect_geometry_type`: a closed tetrahedron is a mesh; PolyData with only lines is `lines`.
- The `.pcd` reader of `pardesline.medical.pyvista_adapter` finds x, y, z through the FIELDS header.
- Raw arrays materialised as PLY: integer colours are written as given (0/1 values were scaled to 255).

Skill scripts
- `pointnet-segmentation/scripts/pointnet_seg.py`: `--seed` (default 0) on every command; `eval`
  reports the same mIoU and `infer` the same labels on every run (both changed between runs).

### Changed defaults
- `simpleitk_segmentation.connected_components` / `watershed` `upper_threshold`: 255 -> image maximum.
- `simpleitk_registration.difference_analysis` `upper_threshold`: 400 -> none.
- `simpleitk_registration.bspline` `scale_factors`: `"1,2,4"` -> `""` (the requested grid, LBFGSB);
  `mesh_coarsening_factor` now applies only with `scale_factors`.
- `registration.ransac_icp_pipeline` `icp_max_iteration`: 30 -> 100. Catalog `voxel_size` default
  0.5 -> 0 (auto), as the scripts already did; its catalog maximum 0.9 is lifted.
- `deformable_registration.cpd_deformable` `beta`: 100 -> 2.
- `pyvista_pointcloud_processing.pv_random_sample` `seed`: -1 -> 0; `pv_clip_plane` origin: (0, 0, 0)
  -> dataset centre.
- `mesh_processing.mesh_to_pcd_uniform` / `mesh_to_pcd_poisson_disk` `seed`: -1 -> 0.
- `point_cloud_reconstruction.poisson` / `ball_pivoting` `normal_radius`: 0.1 -> 0 (3 x point spacing).
- `sdf.compute_sdf` / `occupancy_reconstruction` `mc_allow_degenerate`: true -> false.
- `pyvista_volume_processing.pv_contour` `method`: `contour` -> `auto`; `pv_slice` origin and
  `pv_slice_orthogonal` x, y, z: 0 -> dataset centre when not given.

### New parameters
- `seed` on `simpleitk_registration` rigid, affine, advanced_rigid, bspline (42; 0 is refused, it means
  "wall clock" in SimpleITK), on `registration` ransac_global, icp_refinement, ransac_icp_pipeline,
  on `point_cloud_segmentation.ransac_plane`, `lidar_scene_detection` ground_removal and
  object_clustering, and on `collision_detection` sdf_collision and penetration_depth (0). The seed is
  written to the JSON sidecars of the registration methods.
- `registration.ransac_global` / `ransac_icp_pipeline`: `restarts` (8); the pipeline also
  `icp_coarse_threshold_factor` (1.5), `symmetry_probe` (true), `score_upper_quantile` (0.9),
  `ambiguity_margin` (0.10), `on_ambiguous` (`error` | `warn`).
- `sign_rays` (3) on `sdf` compute_sdf, occupancy_reconstruction, sdf_voxel_visualization,
  `voxel_to_mesh.binary_erosion` and both `collision_detection` methods.
- `register_bspline(..., seed=)` and `seed` in `pardesline.medical` registration options.
- Registration JSON sidecars now carry `voxel_size`, `seed`, `status`, `result_stage`, `threshold`,
  every candidate pose and the Open3D version.

### Silent behaviours that are now errors
- The six `simpleitk_registration` scripts, the three `registration` scripts and `cpd_deformable`
  require `--moving` (without it they registered the input with a moved copy of itself).
- `ransac_icp_pipeline` exits with code 3 when another pose scores within 10 % of the winner
  (`status: "ambiguous"` in the JSON; the output is still written). Pass `on_ambiguous="warn"` to keep
  the old behaviour of always returning the winner.
- Inputs without triangles are refused by `mesh_to_pointcloud`, the two mesh samplers, the three
  `sdf` methods, `binary_erosion` and both collision methods (a point cloud used to be replaced by its
  convex hull, an invented surface).
- Empty results exit with code 1: `object_clustering` with no non-ground point (it wrote its input),
  `gaussian_deformation` reaching no point (it wrote its input), `pv_clip_box`, `pv_clip_plane`,
  `pv_threshold`, `pv_extract_points`, `pv_extract_cells`, `pv_threshold_volume`, `pv_contour`.
- Required instead of unit-scale defaults: `gaussian_deformation` `radius` and `displacement`,
  `pv_clip_box` bounds, `pv_threshold` / `pv_extract_points` `scalars`, `lower`, `upper`
  (`pv_threshold` used to threshold the distance to an arbitrary plane), `ransac_plane`
  `distance_threshold`.
- `cpd_deformable --low_rank true` is refused (pycpd 2 ignored it); `--num_eig` is ignored with a warning.
- `watershed` refuses `distance_inside_is_positive=true` and `distance_squared=true` (both broke the
  seed test).
- `pv_scalar_stats` refuses a vector array and asks for `scalars` when several arrays qualify.
- `pv_contour` refuses `method="contour"` on an oblique volume.
- Unknown colormap numbers are refused by `intensity_colorization`, `depth_colorization` and
  `height_colorization` (they fell back to another colormap).
- `pardesline.medical`: an unknown metric or initializer name raises `ValueError` (they fell back to
  Mattes MI and MOMENTS); DICOM files without position tags that form no series raise; writing an
  oblique volume to `.vti` with PyVista < 0.45 raises instead of dropping the direction.
- `ransac_icp_pipeline --rotation_degrees` is accepted and ignored with a warning (it only drove the
  removed demo mode).

### Documentation
- Help texts, catalog descriptions and theory now say what the code does: `intensity_colorization`
  colours by distance from the origin (no intensity is read), `depth_colorization` by z,
  `depth_filter` keeps quantiles of z, `roi_extraction` is centred on the median point,
  `multi_resolution` is a side-by-side preview, `pv_distance` is the unsigned distance to the
  bounding-box centre, `pv_clip_plane` keeps the side opposite to the normal by default, the B-spline
  method has no bending-energy term, watershed seeds are depth thresholds.
- `docs/audit/2026-11-additional-findings.md`: the 10 additional bugs, in the audit's format.

## [0.3.1](https://github.com/pardesline/pardesline/compare/v0.3.0...v0.3.1) (2026-11-03)


### Fixed

* **docs:** deep links to the docs site go through /latest/ ([6ce583e](https://github.com/pardesline/pardesline/commit/6ce583ef80f6236077cc845aae21ad5f7eef5f91))
* **mcp:** agents close every data-writing task with a four-line report ([3cf0ff4](https://github.com/pardesline/pardesline/commit/3cf0ff456cb1f2ad14c56c694bc17239207dfc9a))
* **packaging:** absolute links in the PyPI description ([924c0d7](https://github.com/pardesline/pardesline/commit/924c0d7e8affc22adb854a6cb511d2f654d3fff3))

## [0.3.0](https://github.com/pardesline/pardesline/compare/v0.2.0...v0.3.0) — 2026-10-17

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
[0.2.0]: https://github.com/pardesline/pardesline/compare/21d6215...v0.2.0
[0.2.0a1]: https://pypi.org/project/pardesline/0.2.0a1/
