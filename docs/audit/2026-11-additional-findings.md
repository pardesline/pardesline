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
