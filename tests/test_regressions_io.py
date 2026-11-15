"""Regression tests for the parts of the code the 2026-11-15 audit did not open (loading,
conversions). "X-n" = docs/audit/2026-11-additional-findings.md."""

from __future__ import annotations

import numpy as np

from pardesline.object.arrays import write_ply


def _read_rgb(path):
    data = path.read_bytes()
    body = data[data.index(b"end_header\n") + len(b"end_header\n") :]
    fields = [("x", "<f8"), ("y", "<f8"), ("z", "<f8"), ("r", "u1"), ("g", "u1"), ("b", "u1")]
    rec = np.frombuffer(body, dtype=fields)
    return np.stack([rec["r"], rec["g"], rec["b"]], axis=1)


def test_x09_integer_colours_are_written_as_given(tmp_path):
    """Integer colours whose values happen to be 0/1 were multiplied by 255."""
    xyz = np.zeros((3, 3))
    rgb = np.array([[0, 1, 0], [1, 1, 1], [0, 0, 1]], dtype=np.uint8)
    out = write_ply(tmp_path / "a.ply", xyz, {"red": rgb[:, 0], "green": rgb[:, 1], "blue": rgb[:, 2]})
    assert np.array_equal(_read_rgb(out), rgb)


def test_x09_float_colours_in_unit_range_are_scaled(tmp_path):
    xyz = np.zeros((2, 3))
    rgb = np.array([[0.0, 0.5, 1.0], [1.0, 0.0, 0.2]])
    out = write_ply(tmp_path / "b.ply", xyz, {"r": rgb[:, 0], "g": rgb[:, 1], "b": rgb[:, 2]})
    assert np.array_equal(_read_rgb(out), np.rint(rgb * 255).astype(np.uint8))
