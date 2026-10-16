"""The code blocks in the README, the tutorial and the how-to pages run as written.

Every ``python`` block of the listed pages is executed in one namespace per page,
in a temporary working directory, with the display calls neutralised. Blocks that
reference files the reader must supply (``scan_a.ply``, ``/data/my_study``) are
skipped by the ``PLACEHOLDERS`` filter (their imports still carry over); everything
else must run. These tests download bundled datasets, so they run only with
``PARDESLINE_NETWORK_TESTS=1``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.network,
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("PARDESLINE_NETWORK_TESTS"), reason="set PARDESLINE_NETWORK_TESTS=1"
    ),
]

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "README.md",
    "docs/getting-started/tutorial.md",
    "docs/how-to/download-a-medical-imaging-dataset-in-python.md",
    "docs/how-to/register-two-point-clouds-with-icp-in-python.md",
    "docs/how-to/register-ct-and-mri-of-the-same-patient-in-python.md",
    "docs/how-to/turn-a-segmentation-mask-into-a-mesh-in-python.md",
    "docs/how-to/segment-organs-in-a-ct-scan-in-python.md",
    "docs/how-to/reconstruct-a-surface-from-a-point-cloud-in-python.md",
    "docs/how-to/load-raw-npy-and-bin-point-clouds-with-a-layout.md",
    "docs/how-to/convert-a-point-cloud-to-gaussian-splats-in-python.md",
    "docs/how-to/extract-dinov3-features-from-medical-images-in-python.md",
]
# A block containing any of these refers to files or state the reader supplies.
PLACEHOLDERS = (
    "scan_a",
    "scan_b",
    "scan.ply",
    "new_scan",
    "atlas.ply",
    "labels.npy",
    "/data/",
    "0000000000.bin",
    "frame.npz",
    'pl.load("seg.nii.gz")',
    'pl.load("ct.nii.gz")',
    'pl.load("mr.nii.gz")',
    "input.ply",
    "fixed.ply",
    "moving.ply",
    "splat.ply",
    "preds/",
    "some-org",
    "hf_kits23",
    "tcia_",
    "fetch_all()",
    "pl.scan(",
    "totalsegmentator_ct",
    "diag",
    "TransformationEstimationPointToPoint",  # the README comparison fragments, not runnable blocks
    "aligned = target.align(moving)",
)
NEUTRALISE = {
    ".plot()": ".n_points",
    "p.show()": "p.close()",
}


def blocks(page: Path) -> list[str]:
    text = page.read_text(encoding="utf-8")
    return re.findall(r"```python\n(.*?)```", text, re.S)


@pytest.mark.parametrize("rel", PAGES)
def test_page_code_blocks_run(rel, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYVISTA_OFF_SCREEN", "true")
    namespace: dict = {}
    ran = 0
    for code in blocks(ROOT / rel):
        if any(p in code for p in PLACEHOLDERS):
            # keep the imports so later blocks of the page can rely on them
            imports = [line for line in code.splitlines() if line.startswith(("import ", "from "))]
            exec(compile("\n".join(imports), f"{rel}:imports", "exec"), namespace)
            continue
        for old, new in NEUTRALISE.items():
            code = code.replace(old, new)
        exec(compile(code, f"{rel}:block{ran}", "exec"), namespace)
        ran += 1
    assert ran >= 1, f"{rel}: no runnable block found"
