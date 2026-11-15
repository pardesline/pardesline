"""Regression tests for the second batch of the 2026-11-15 audit (design improvements).

"P1-21" = Part 1 entry 21, "P2-Bn" / "P3-Bn" = Part 2 / Part 3 entry Bn. Synthetic data, no network.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

sitk = pytest.importorskip("SimpleITK")


@pytest.mark.medical
@pytest.mark.parametrize("fn_name", ["register_rigid", "register_affine"])
def test_p1_21_default_optimiser_converges_on_simple_cases(fn_name):
    """With plain gradient descent and 1 % sampling, a sphere shifted by (2, -1, 0.5) mm 'registered'
    7.5 m away (exit 0) and blobs rotated 8 degrees ended 5-9 mm off."""
    from _synthetic import blob_volume, moved_copy, tre

    from pardesline.medical import _service as svc

    fn = getattr(svc, fn_name)
    z, y, x = np.mgrid[0:32, 0:32, 0:32]
    sph = sitk.GetImageFromArray(
        (((x - 16) ** 2 + (y - 16) ** 2 + (z - 16) ** 2) < 100).astype(np.float32) * 200 + 10
    )
    shift = sitk.TranslationTransform(3, (2.0, -1.0, 0.5))
    moved = sitk.Resample(sph, sph, shift, sitk.sitkLinear, 10.0, sph.GetPixelID())
    _, tx = fn(sph, moved, metric="mean_squares", num_iterations=30)
    assert tre(tx, shift.GetInverse(), np.array([[16.0, 16.0, 16.0], [10.0, 16.0, 20.0]])) < 0.5

    fixed, pts = blob_volume(size=(48, 48, 40), spacing=(1.5, 1.5, 2.0))
    s_map = sitk.Euler3DTransform(
        (0, 0, 0), math.radians(6), math.radians(-4), math.radians(8), (5.0, -3.0, 4.0)
    )
    _, tx = fn(fixed, moved_copy(fixed, s_map))
    assert tre(tx, s_map.GetInverse(), pts) < 1.0
