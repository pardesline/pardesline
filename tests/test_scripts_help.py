"""Every one of the 73 scripts imports cleanly and answers --help.
This catches a missing dependency, a broken import or a syntax error in any
algorithm without running it on data."""

from __future__ import annotations

import subprocess
import sys

import pytest

from pardesline.catalog import load_catalog

MEDICAL_MODULES = {"simpleitk_registration", "simpleitk_segmentation"}


def _mark(method):
    return pytest.param(
        method,
        id=method.qualname,
        marks=[
            pytest.mark.slow,
            pytest.mark.medical if method.module_id in MEDICAL_MODULES else pytest.mark.local,
        ],
    )


@pytest.mark.parametrize("method", [_mark(m) for m in load_catalog().methods])
def test_script_help(method):
    proc = subprocess.run(
        [sys.executable, "-m", method.python_module, "--help"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**__import__("os").environ, "MPLBACKEND": "Agg", "PYVISTA_OFF_SCREEN": "true"},
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "--input" in proc.stdout and "--output" in proc.stdout
