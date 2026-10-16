"""3D JEPA self-supervised pretraining on MSD hippocampus MRIs (reference implementation).

    pip install "pardesline[all]" torch
    python examples/jepa_hippocampus/run.py                 # small model, CPU, a few minutes

Runs ``jepa3d_pretrain.py`` from the ``jepa-pretraining`` skill on eight
hippocampus volumes: context encoder (3D ViT) -> predictor -> L2 against an
EMA target encoder on masked blocks. Sizes are reduced so it runs on a laptop;
the real recipe (crop 96, dim 384, 100 epochs) is in the skill.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

HERE = Path(__file__).parent
run(
    "jepa-pretraining",
    "jepa3d_pretrain.py",
    "--dataset",
    "msd_task04_hippocampus",
    "--role",
    "mri",
    "--modality",
    "mr",
    "--take",
    "8",
    "--crop",
    "32",
    "--patch",
    "8",
    "--dim",
    "96",
    "--depth",
    "2",
    "--heads",
    "4",
    "--epochs",
    "3",
    "--batch",
    "4",
    "--out",
    str(HERE / "runs"),
)
