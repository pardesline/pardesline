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
      thresholded = sitk.BinaryThreshold(diff, lowerThreshold=lower_threshold,
                                          upperThreshold=upper_threshold, insideValue=1, outsideValue=0)
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
  init_method = (sitk.CenteredTransformInitializerFilter.GEOMETRY
                if method == "GEOMETRY" else
                sitk.CenteredTransformInitializerFilter.MOMENTS)
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
