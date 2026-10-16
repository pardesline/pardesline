"""<Algorithm or model> on <dataset>: one line on what the example shows.

pip install "pardesline[all]"
python examples/<slug>/run.py        # writes <slug>.png and result.json next to this file
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pyvista as pv

import pardesline as pl

HERE = Path(__file__).parent
SLUG = HERE.name

t0 = time.perf_counter()
ds = pl.load("open3d_bunny")  # a bundled dataset; the licence line is printed
obj = ds[0].mesh  # one object of one sample
result = obj.to_points(num_points=20000, seed=1).clean()  # one algorithm at the catalog defaults
elapsed = time.perf_counter() - t0

summary = {"dataset": ds.name, "input": obj.info(), "output": result.info(), "seconds": round(elapsed, 1)}
(HERE / "result.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
print(json.dumps(summary, indent=1, default=str))

p = pv.Plotter(off_screen=True, window_size=(900, 600))
p.add_points(result.to_pyvista(), color="#f0a05a", point_size=2)
p.add_text(f"{SLUG}: {ds.name}", font_size=11)
p.screenshot(HERE / f"{SLUG}.png")
print("wrote", HERE / f"{SLUG}.png")
