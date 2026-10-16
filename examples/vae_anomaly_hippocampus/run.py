"""VAE reconstruction-based anomaly detection on hippocampus MRI slices.

    pip install "pardesline[all]" torch pillow
    python examples/vae_anomaly_hippocampus/run.py          # a few minutes on CPU

Mid-axial slices of the first 24 MSD hippocampus MRIs are written as PNG
(the "normal" set); ``vae_anomaly.py`` from the ``vae-anomaly-detection``
skill trains a small VAE on them and scores eight held-out slices, two of
which carry a synthetic bright lesion. Scores and residual heat-maps land in
./scores.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

import pardesline as pl

HERE = Path(__file__).parent
normal, test = HERE / "slices_normal", HERE / "slices_test"
normal.mkdir(exist_ok=True)
test.mkdir(exist_ok=True)

cases = pl.load("msd_task04_hippocampus").filter(split="Tr").take(32)
for i, case in enumerate(cases):
    vol = case.mri.to_numpy().astype(np.float32)  # (z, y, x)
    sl = vol[vol.shape[0] // 2]
    sl = (255 * (sl - sl.min()) / (np.ptp(sl) + 1e-6)).astype(np.uint8)
    img = Image.fromarray(sl).resize((64, 64))
    if i < 24:
        img.save(normal / f"{case.id}.png")
    else:
        arr = np.asarray(img).copy()
        if i % 4 == 0:  # synthetic lesion: a bright 8-pixel disc
            yy, xx = np.ogrid[:64, :64]
            arr[(yy - 30) ** 2 + (xx - 34) ** 2 < 64] = 255
            Image.fromarray(arr).save(test / f"{case.id}_lesion.png")
        else:
            Image.fromarray(arr).save(test / f"{case.id}.png")

run(
    "vae-anomaly-detection",
    "vae_anomaly.py",
    "train",
    "--normal",
    str(normal),
    "--out",
    str(HERE / "runs"),
    "--epochs",
    "80",
    "--size",
    "64",
    "--latent",
    "32",
    "--batch",
    "8",
)
run(
    "vae-anomaly-detection",
    "vae_anomaly.py",
    "score",
    "--weights",
    str(HERE / "runs" / "vae.pt"),
    "--images",
    str(test),
    "--out",
    str(HERE / "scores"),
)

# One image: each test slice, its reconstruction, the residual heat-map and the score (lesions are marked).
import csv

from PIL import ImageDraw

with open(HERE / "scores" / "scores.csv", encoding="utf-8") as fh:
    scores = {r["file"]: float(r["score"]) for r in csv.DictReader(fh)}
names = sorted(scores, key=scores.get, reverse=True)
tile, pad = 96, 6
sheet = Image.new("RGB", (3 * (tile + pad) + pad, len(names) * (tile + pad) + pad + 18), "black")
draw = ImageDraw.Draw(sheet)
draw.text((pad, 2), "slice | reconstruction | residual     score (lesion slices marked *)", fill="white")
for row, name in enumerate(names):
    y = 18 + pad + row * (tile + pad)
    for col, suffix in enumerate(("", "_recon", "_residual")):
        src = (test / f"{name}.png") if suffix == "" else (HERE / "scores" / f"{name}{suffix}.png")
        sheet.paste(
            Image.open(src).convert("RGB").resize((tile, tile), Image.NEAREST), (pad + col * (tile + pad), y)
        )
    draw.text(
        (3 * (tile + pad) + pad - 60, y + 2),
        f"{scores[name]:.2f}{' *' if 'lesion' in name else ''}",
        fill="white",
    )
sheet.save(HERE / "vae_anomaly.png")
print("wrote", HERE / "vae_anomaly.png")
