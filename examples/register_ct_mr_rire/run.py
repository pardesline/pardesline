"""Rigid CT / MR registration on the RIRE brain pair, the README 30-second demo.

    pip install "pardesline[all]"
    python examples/register_ct_mr_rire/run.py            # writes rire_ct_mr.png next to this file

Loads the RIRE training_001 CT and MR-T1 (19 MB, two files, checksummed),
registers the MR onto the CT (SimpleITK rigid, Mattes mutual information,
geometry-centred initialisation: the catalog defaults) and renders the CT
slice before and after the MR overlay.
"""

from pathlib import Path

import pyvista as pv

import pardesline as pl

OUT = Path(__file__).with_name("rire_ct_mr.png")

s = pl.load("rire_brain")[0]  # CT + MR T1 of one head; the licence line is printed, never guessed
moved = s.ct.align(s.mr_t1)  # rigid registration; moved.transform holds the Euler angles and translation
print(
    moved.transform["sub_transforms"][0]["rotation_deg"],
    moved.transform["sub_transforms"][0]["translation_mm"],
)

ct, mr = s.ct.to_pyvista(), moved.to_pyvista()
p = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(1200, 520))
p.subplot(0, 0)
p.add_mesh(ct.slice("z"), cmap="gray", show_scalar_bar=False)
p.add_text("CT (fixed)", font_size=11)
p.view_xy()
p.subplot(0, 1)
p.add_mesh(ct.slice("z"), cmap="gray", show_scalar_bar=False)
p.add_mesh(mr.slice("z"), cmap="magma", opacity=0.55, show_scalar_bar=False)
p.add_text("MR T1 registered onto the CT", font_size=11)
p.view_xy()
p.screenshot(OUT)
print("wrote", OUT)
