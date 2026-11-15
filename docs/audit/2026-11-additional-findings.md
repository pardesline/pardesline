---
title: Correctness audit, November 2026 — additional findings
description: Bugs found in pardesline while fixing the 2026-11-15 audit, beyond the audit's own list, with reproduction, measured effect, fix and regression test.
---

# Correctness audit, November 2026: additional findings

The audit of 2026-11-15 (`PLATFORM_CODE_BUGS.md`, kept outside this repository) listed 48 bugs in the
algorithm code that this package shares with the platform. While fixing them, every catalogued
algorithm and the code the audit did not open (loading, the object model, conversions, the runner,
the catalog, the scripts bundled in `skills/`) was checked against synthetic data with a known
answer. This page records the **additional** bugs found that way, in the audit's format.

Rules followed for every entry:

- reproduced first by a test that fails on the code of 0.3.1, then fixed;
- the test builds its own data with a known answer and a fixed seed, and is named `test_x<NN>_…`
  in `tests/test_regressions_*.py`;
- a suspicion that could not be reproduced is listed at the end as a suspicion, not as a bug.

Severity words: wrong result silently / crash / misleading output / cosmetic.

## Medical volumes

### X1. Difference analysis does not count the largest differences

- File: `src/pardesline/medical/_service.py`, function `compute_difference_thresholded`
  (used by `ops/simpleitk_registration/difference_analysis.py`); default also in the script
  (`--upper_threshold 400`) and in the catalog.
- Faulty code:
  ```python
  def compute_difference_thresholded(fixed, registered, lower_threshold=50.0, upper_threshold=400.0):
      ...
      thresholded = sitk.BinaryThreshold(
          diff, lowerThreshold=lower_threshold, upperThreshold=upper_threshold, insideValue=1, outsideValue=0
      )
      high_diff_voxels = int(np.count_nonzero(sitk.GetArrayFromImage(thresholded)))
  ```
- What goes wrong: `high_diff_voxels` / `high_diff_percentage`, the summary of misalignment, count
  only the voxels whose difference lies in [50, 400]. A voxel off by 1000 (a worse misalignment,
  common in CT where bone against air is 1000-2000 HU) is not counted, so a worse alignment can
  report a better score. Same family as audit entries P1-6 and P1-7 (hard-coded upper bound).
- Measured: zero image against an image with 200 voxels at 100 and 200 voxels at 1000:
  `high_diff_voxels` = 200 (expected 400), `high_diff_percentage` 20 % instead of 40 %.
- Corrected code: `upper_threshold=None` by default, meaning the maximum of the difference image;
  an explicit value still bounds the range.
- Severity: misleading output.
- Test: `test_x01_difference_analysis_counts_every_large_difference`.

### X2. Watershed (corrected version of the audit): a seedless object takes a neighbour's label

- File: `src/pardesline/medical/_service.py`, function `segment_watershed`, in the correction
  proposed by the audit for its entry 9.
- Faulty code (audit's corrected snippet):
  ```python
  ws = sitk.MorphologicalWatershedFromMarkers(dist, seeds, ...)
  ws = sitk.Mask(ws, sitk.Cast(cleaned, sitk.sitkUInt8))
  ```
- What goes wrong: the watershed floods the whole image, background included. A separate object too
  thin to hold a seed (shallower than `seed_radius`) is reached through the background by the basin
  of a neighbouring object and keeps that object's label after masking: two disconnected objects
  share one label, and their measured volume is summed. When the absorbed object touches the image
  border, the border removal then deletes the neighbour as well.
- Measured: ball of radius 10 mm and a separate ball of radius 4 mm (seed radius 7 mm, 1 mm voxels):
  the small ball carried the large ball's label. In the audit's own phantom with an extra ball cut
  by the border, the large ball next to it was deleted (1 of 2 objects left).
- Corrected code: after masking, voxels of every connected component of the mask that contains no
  seed are set to 0:
  ```python
  parts = sitk.GetArrayFromImage(sitk.ConnectedComponent(cleaned, True))
  seeded = np.unique(parts[sitk.GetArrayViewFromImage(seeds) > 0])
  a[~np.isin(parts, seeded[seeded != 0])] = 0
  ```
  (a background marker was tried first and rejected: ties in the flooding order gave the object
  rims to the background, 38 % of a ball lost.)
- Severity: wrong result silently.
- Tests: `test_x02_watershed_does_not_give_a_seedless_object_its_neighbours_label`,
  `test_p1_09_watershed_splits_touching_objects_and_drops_border_objects`.

### X3. Initializer name silently replaced by MOMENTS

- File: `src/pardesline/medical/_service.py`, function `get_initial_transform` (used by
  `register_rigid`).
- Faulty code:
  ```python
  init_method = (
      sitk.CenteredTransformInitializerFilter.GEOMETRY
      if method == "GEOMETRY"
      else sitk.CenteredTransformInitializerFilter.MOMENTS
  )
  ```
- What goes wrong: any value other than the exact string `"GEOMETRY"` (for example `"geometry"`, as
  `register_affine` accepts, or a typo) runs the MOMENTS initializer without a message.
- Measured: blob volume translated by 3 mm: `"GEOMETRY"` gave translation (0, 0, 0), `"geometry"`
  gave (-2.957, 0.003, 0), the MOMENTS result.
- Corrected code: upper-case the name, accept GEOMETRY or MOMENTS, raise `ValueError` otherwise.
- Severity: wrong result silently (Python API; the command line restricts the choices).
- Test: `test_x03_initializer_name_is_not_silently_replaced`.

### X4. Unknown metric name silently runs Mattes mutual information

- File: `src/pardesline/medical/_service.py`, function `_configure_registration`.
- Faulty code:
  ```python
  elif metric == "joint_histogram_mi":
      reg.SetMetricAsJointHistogramMutualInformation()
  else:
      reg.SetMetricAsMattesMutualInformation(...)
  ```
- What goes wrong: `register_rigid(..., metric="mean_square")` (missing "s") registers with mutual
  information and reports success.
- Measured: `_configure_registration(reg, metric="mean_square")` returned without error.
- Corrected code: an explicit `elif metric == "mattes_mutual_information"` and `ValueError` for any
  other name.
- Severity: wrong result silently (Python API; the command line restricts the choices).
- Test: `test_x04_unknown_metric_name_is_an_error`.

## Point clouds

### X5. CPD registers the fixed cloud with a deformed copy of itself when `--moving` is omitted

- File: `src/pardesline/ops/deformable_registration/cpd_deformable.py`, `main`, the `else` branch
  after `if args.moving:` (lines 56-82 of 0.3.1).
- Faulty code:
  ```python
  parser.add_argument("--moving", default=None, ...)
  ...
  else:
      logger.info("No --moving provided, creating synthetic deformed target (demo mode)")
      source_pts_world = target_pts_world.copy()
  ```
- What goes wrong: the same failure as audit entries P1-20 and P2-A1, in a script the audit did not
  list for it: a forgotten argument produces a normal-looking output of a registration that never
  involved the second cloud, with exit code 0.
- Measured: `cpd_deformable.py --input fixed.ply --output o.ply` exited 0 and wrote a result.
- Corrected code: `--moving` is required (argparse exits with code 2 without it); the demo branch is
  removed.
- Severity: misleading output.
- Test: `test_x05_cpd_requires_moving`.

### X6. RANSAC plane fits are not seeded

- Files: `src/pardesline/ops/point_cloud_segmentation/ransac_plane.py`,
  `src/pardesline/ops/lidar_scene_detection/ground_removal.py`,
  `src/pardesline/ops/lidar_scene_detection/object_clustering.py` (`pcd.segment_plane(...)`).
- What goes wrong: `segment_plane` draws its samples from Open3D's global random generator, which no
  script seeded: the plane, the inliers and everything downstream (ground removal, clusters) change
  from run to run. Same class as audit entry P2-A3, in three scripts it did not list.
- Measured: on the audit's SCENE (plane of 8000 points, two spheres, 150 outliers) with 20
  iterations, repeated runs gave different inlier sets before the fix and identical ones after.
- Corrected code: a `seed` parameter (default 0) and `o3d.utility.random.seed(args.seed)` before
  `segment_plane`, plus the single-thread setting of X7.
- Severity: misleading output (non-reproducible results).
- Test: `test_x06_plane_ransac_is_seeded` (two scripts; object_clustering shares the code path).

### X7. Seeding Open3D's RANSAC does not make it reproducible (the audit's fix for P2-A3 is incomplete)

- Files: `src/pardesline/ops/registration/*.py` and the three scripts of X6.
- What goes wrong: Open3D runs RANSAC iterations in parallel OpenMP threads that draw from one
  global generator, so the sequence each iteration receives depends on thread scheduling. With
  `o3d.utility.random.seed(s)` alone, as the audit proposes, two runs with the same seed still differ.
  The audit's claim "with a fixed seed, repeated runs gave identical matrices" did not hold here
  (Open3D 0.19.0, Windows, 16 threads).
- Measured: `ransac_global` on a near-symmetric 4000-point pair, `--seed 5 --restarts 2`, three runs:
  rotation errors 5.06, 7.15 and 5.06 degrees with the default thread count; 5.06 degrees three
  times with `OMP_NUM_THREADS=1` (run time 13.5 s -> 19.7 s for the three runs).
- Corrected code: each RANSAC script sets the variable before importing Open3D:
  ```python
  import os

  os.environ["OMP_NUM_THREADS"] = "1"  # must precede "import open3d"
  ```
  It takes effect in the process that runs the script (the runner always starts one); a caller that
  imports a script's `main` into a process where Open3D is already loaded keeps its thread count.
- Severity: misleading output (non-reproducible results under a seed).
- Test: `test_p2_a03_x07_same_seed_same_result`, `test_x06_plane_ransac_is_seeded` (both run the
  scripts in a fresh interpreter, as the runner does).

### X8. `height_colorization` accepts any colormap number

- File: `src/pardesline/ops/lidar_scene_detection/height_colorization.py`, `main`.
- Faulty code: `cmap_name = cmap_names.get(args.colormap, 'viridis')`.
- What goes wrong: a number outside 0-3 silently uses viridis (same pattern as P2-A16's colormap
  legends).
- Measured: `--colormap 9` exited 0.
- Corrected code: `choices=[0, 1, 2, 3]` (argparse error otherwise); catalog `max` 3.
- Severity: cosmetic.
- Test: `test_x08_height_colorization_unknown_colormap_is_an_error`.

### Note on audit entry P2-A4 (two ICP passes)

Two passes (1.5 v then 0.4 v) are a large improvement but not a complete fix on near-symmetric
parts: from 20 starts off by 5 degrees and N(0, 2v), one pass at 0.4 v ended above 0.1 mm in 18,
two passes in 1 (box-like part with small features). The remaining case is what the pipeline's
restarts with a threshold-free score and the symmetry probe are for.

## Meshes and surfaces

No additional bug was found in this area. Checked against known answers: PyVista mean and Gaussian
curvature of a sphere of radius 10 (median 0.1 and 0.01), decimation (`target_reduction 0.75`
keeps 25 % of the faces), Open3D quadric simplification (500 faces asked, 500 obtained), midpoint
subdivision (x4 faces), Laplacian and Taubin smoothing (volume change -0.05 % and +0.001 %), vector
magnitude ((3, 4, 0) -> 5), feature edges of a cube (12), convex hull of a sphere (volume equal), and,
after the fixes, the SDF, occupancy, erosion, Poisson and ball-pivoting outputs (outward, volume
within 1-2 %).

### Suspicion not reproduced: Poisson / ball pivoting with inward normals

`poisson.py` and `ball_pivoting.py` orient estimated normals with
`orient_normals_consistent_tangent_plane`, which makes them consistent but leaves the global sign
undetermined; an inward orientation would give an inside-out surface. Not reproduced: with the
normal radius fixed (audit entry P3-A4), 12 runs (sphere and torus clouds, three samplings, both
methods) all gave a positive signed volume within 1 % of the exact one. Not fixed; the scripts now
log the signed volume so that the case would be visible.

### Note on audit entry P3-A9

`method="marching_cubes"` honours the direction matrix as `flying_edges` does (centroid error 0 on
the 25-degree oblique ball); only `contour` ignores it. The new `auto` default picks `flying_edges`
on image data, and an explicit `contour` on an oblique volume exits with an error.

## Code the audit did not open: loading, object model, conversions, skill scripts

### X9. `write_ply` scales integer colours by 255 when their maximum is at most 1

- File: `src/pardesline/object/arrays.py`, function `write_ply` (used to materialise raw arrays
  such as KITTI `.bin` or `.npy` point clouds as PLY).
- Faulty code:
  ```python
  rgb = np.stack([np.asarray(attrs.pop(k), dtype=np.float64) for k in names], axis=1)
  if rgb.max() <= 1.0:
      rgb = rgb * 255.0
  ```
- What goes wrong: the scale of the colours is guessed from their values, after they have been cast
  to float. Integer colours whose values happen to be 0 or 1 (a mask or label encoded in a colour
  channel, a very dark cloud) are written as 0 / 255.
- Measured: uint8 colours `[[0, 1, 0], [1, 1, 1], [0, 0, 1]]` were written as `[[0, 255, 0], ...]`.
- Corrected code: scale only floating-point colours whose maximum is at most 1; integer colours are
  written as given.
- Severity: wrong result silently (rare input).
- Tests: `test_x09_integer_colours_are_written_as_given` (fails on 0.3.1),
  `test_x09_float_colours_in_unit_range_are_scaled` (guard: passes on both).

### Checked without finding a bug

- `object/frame.py`, `object/convert.py`: the frame of an ITK volume comes from its header (LPS, mm);
  formats that carry no frame stay unknown; the 4x4 affine scales the direction columns by the
  spacing (index -> world); `volume_to_mesh` keeps the direction matrix (contour on an `ImageData`
  with `direction_matrix`, flying edges).
- `object/arrays.py`: headerless arrays need an explicit dtype and shape; `(L, W, H)` grids are
  transposed to SimpleITK's `(z, y, x)`; `.npy` / `.npz` dtypes are cross-checked, not cast.
- Runner and catalog: parameters are validated against the catalog and passed only when given, so a
  `null` default leaves the script's own default in force.
- Skill scripts that run without PyTorch: `metrics3d.py` self-test, `rigid_ct_mr.py` (seeded
  sampling, composite unwrapped), `registration_eval.py` and `atlas_label_transfer.py` (pose error
  in the moving-to-fixed convention used by the scripts).

### X10. PointNet skill script: evaluation and inference change from run to run

- File: `skills/pointnet-segmentation/scripts/pointnet_seg.py`, `NpzClouds.__getitem__` (used by
  `eval`) and `cmd_infer`.
- Faulty code:
  ```python
  idx = np.random.choice(len(pts), self.num_points, replace=len(pts) < self.num_points)  # unseeded
  ...
  order = np.random.permutation(len(xyz))
  for start in range(0, len(order), n):
      idx = order[start : start + n]
      if len(idx) < n:
          idx = np.concatenate([idx, np.random.choice(order, n - len(idx))])
      logits, _ = model(torch.from_numpy(feats[idx].T[None]).to(device))
      labels[idx] = logits.argmax(1)[0].cpu().numpy()
  ```
- What goes wrong: nothing is seeded. `eval` scores a random subsample of each cloud, so the
  reported accuracy and mIoU differ between runs with the same weights. `infer` cuts the cloud into
  random chunks (PointNet's global feature depends on the chunk), and the points used to pad the last
  chunk overwrite the labels they already received in their own chunk.
- Measured (PyTorch 2.15 CPU, two-class sphere data, 15 training epochs): two `eval` runs gave mIoU
  0.596 and 0.608; three `infer` runs on one 1300-point scan differed in 7 labels.
- Corrected code: a `--seed` option (default 0) on every command seeds NumPy, Python and torch;
  inference draws its chunk order from `default_rng(seed)` and keeps only the predictions of the
  real points of the padded chunk.
- Severity: misleading output (non-reproducible scores and labels).
- Test: `test_x10_pointnet_eval_and_inference_are_reproducible` (needs torch; skipped without it).

### Suspicions not reproduced or not reachable

- The other PyTorch skill scripts (`vae_anomaly.py`, `dinov3_*`, `jepa3d_pretrain.py`) use random
  augmentation during training; training randomness is expected, and their evaluation paths were
  not run here (the DINOv3 and JEPA scripts need model weights or datasets that are downloaded).
  Not checked against a known answer.

## Core: saving, licences, catalog (0.5.0)

Found while fixing the nine items of a downstream review of 0.3.1 (object saving, registration
quality, licences, label volumes, runner, manifests).

### X11. A non-commercial licence is lost when the object is saved

- File: `src/pardesline/object/frame.py`, `License.to_dict`.
- Faulty code:
  ```python
  return {k: v for k, v in asdict(self).items() if v not in (None, "unknown", False)}
  ```
- What goes wrong: `commercial=False` is dropped together with the values that state nothing, so
  the sidecar written by `save()` (and every licence record returned to an agent) omits the
  restriction; the object reloads as "commercial use unknown".
- Measured: a CC-BY-NC-4.0 cloud saved and reloaded had `commercial=None`.
- Corrected code: leave out only `None`, `redistribution="unknown"` and `requires_agreement=False`.
- Severity: misleading output.
- Test: `test_x11_non_commercial_survives_a_save`.

### X12. Lengths in file units refused for data in millimetres

- File: `src/pardesline/catalog/data/*.json`, twenty parameters (voxel sizes, radii, DBSCAN eps,
  plane thresholds, alpha, SDF clamp band, collision obstacle size and overlap).
- Faulty data: `"max": 0.05` for `compute_sdf.voxel_size`, `"max": 0.5` for
  `voxel_downsample.voxel_size` and `dbscan_clustering.eps`, and so on.
- What goes wrong: `pl.run` and the MCP run tool validate parameters against these bounds, so
  every sensible value for data in millimetres raised `ParameterError`; only the unit-scale
  defaults could run. Loud, but it made the methods unusable on most medical and industrial data.
- Measured: the published 0.4.0 wheel refused `compute_sdf voxel_size=0.5`.
- Corrected data: bounds (1e-9, 1e9) for lengths in file units (clamp band (-1e9, 0) / (0, 1e9)).
- Severity: crash (refusal of valid input).
- Test: `test_x12_lengths_in_file_units_accept_millimetre_values` (20 cases).

### X13. `sdf_voxel_visualization` clamps the requested resolution

- File: `src/pardesline/ops/sdf/sdf_voxel_visualization.py`, `main`.
- Faulty code: `res = max(8, min(128, args.resolution))`.
- What goes wrong: `--resolution 256` runs at 128 without a message.
- Corrected code: a resolution outside 8-128 exits 1 with the allowed range.
- Severity: misleading output.
- Test: `test_p3_b02_x13_sdf_band_follows_the_grid_and_resolution_is_not_clamped`.

### X14. Saves that wrote one format under another extension (beyond the reported `.stl` case)

- File: `src/pardesline/object/__init__.py`, `Object.save`.
- What goes wrong: three more paths copied bytes into a file of another type: a DICOM folder saved
  to any volume extension received the materialised `.mha` bytes; a raw array saved to any
  extension received the materialised `.ply` / `.mha` bytes; `x.mhd` saved as `y.mhd` copied a
  header that still names `x.raw` as its data file.
- Corrected code: every save goes through `convert.save_as` (copy for the same extension,
  conversion when a writer exists, `ValueError` otherwise); `.mhd` is always rewritten.
- Severity: wrong result silently.
- Tests: `tests/test_regressions_save.py` (642 cells), `test_i02_mhd_saved_under_another_name_points_at_its_own_data`.

### X15. Open3D writes GLB files other readers reject

- Where: `open3d.io.write_triangle_mesh(..., ".glb")`, Open3D 0.19.
- What goes wrong: the file has the `glTF` magic but Assimp reports "buffer view out of range"
  and VTK "no valid BIN chunks"; Open3D itself reads it back with 0 triangles. The same mesh
  written as `.gltf` reads back correctly with both readers.
- Decision: `.glb` is not offered as a save target (refused with the list of targets); `.gltf` is.
- Severity: wrong result silently (had it been offered).
- Test: the `mesh.* -> .glb` cells of the save matrix expect a refusal.

### Item notes

- Item 3 (registration quality): the floors exposed second-batch entry P1-21 at once. Default
  rigid registration (plain gradient descent, 1 % sampling) put a sphere shifted by 2 mm 7.5 m
  away with exit code 0, and `tests/test_ops_smoke.py::test_volume_segmentation_and_registration`
  passed on that result because it checked only that a transform was written. With the
  regular-step optimiser (now the default) the same case lands within 0.06 mm.
- Item 3: fitness cannot catch every wrong pose: on a 40 %-overlap pair, ICP alone slid 60 degrees
  with fitness 0.84 (the pipeline reported that case as ambiguous). The floors catch failed and
  meaningless registrations, not small errors.
- Item 6: `load_volume` keeps float32 by default (registration and filtering expect it); label maps
  are read with their stored type.
- Item 8: archives are read by HTTP Range and are often several GB; the pin is the server's size
  and ETag per URL, checked when the archive is opened, not a checksum of the content.
