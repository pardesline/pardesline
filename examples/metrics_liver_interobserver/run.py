"""Inter-observer Dice and HD95 between three radiologists on one liver tumour CT.

    pip install "pardesline[medical]"
    python examples/metrics_liver_interobserver/run.py

Runs the ``evaluation-metrics-3d`` reference implementation on the
``liver_tumor_patient01`` dataset (2 MB, one CT and three expert masks): the
numbers show how far two experts are from each other, which is the ceiling
any segmentation model should be measured against.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

run("evaluation-metrics-3d", "metrics3d.py", "--dataset", "liver_tumor_patient01")
