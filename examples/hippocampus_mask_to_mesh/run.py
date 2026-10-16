"""Segmentation mask to surface mesh on the Medical Segmentation Decathlon hippocampus task.

    pip install "pardesline[all]"
    python examples/hippocampus_mask_to_mesh/run.py        # writes hippocampus.png and hippocampus_anterior.stl

The first labelled case is fetched from the official MSD tar (28 MB, read by
HTTP Range; the first run indexes the archive). The label map knows its
labels (1 = anterior, 2 = posterior) from the manifest, so ``to_mesh(label=1)``
is the exact boundary of the anterior hippocampus in LPS millimetres. Taubin
smoothing (catalog defaults) removes the voxel staircase, the STL is written
with a sidecar that records the frame, the licence and both steps.
"""

from pathlib import Path

import pyvista as pv

import pardesline as pl

HERE = Path(__file__).parent

case = pl.load("msd_task04_hippocampus").filter(split="Tr")[0]
anterior = case.mask.to_mesh(label=1).smooth()  # exact boundary, then Taubin smoothing
posterior = case.mask.to_mesh(label=2).smooth()
anterior.save(HERE / "hippocampus_anterior.stl")  # + hippocampus_anterior.stl.pardesline.json
print(case.mask.labels, anterior.info())

p = pv.Plotter(off_screen=True, window_size=(900, 600))
p.add_mesh(case.mri.to_pyvista().slice_orthogonal(), cmap="gray", opacity=0.85, show_scalar_bar=False)
p.add_mesh(anterior.to_pyvista(), color="#f0a05a", smooth_shading=True, label="anterior")
p.add_mesh(posterior.to_pyvista(), color="#5aa0f0", smooth_shading=True, label="posterior")
p.add_legend()
p.add_text("MSD Task04 hippocampus_001: label map -> meshes", font_size=11)
p.screenshot(HERE / "hippocampus.png")
print("wrote", HERE / "hippocampus.png")
