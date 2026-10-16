"""Threshold segmentation of a CT from the Medical Segmentation Decathlon spleen task.

    pip install "pardesline[all]"
    python examples/spleen_ct_threshold_segmentation/run.py    # writes spleen_ct.png

One portal-venous CT (about 30 MB) is fetched out of the official 1.6 GB MSD
tar by HTTP Range. ``segment(lower, upper)`` thresholds in Hounsfield units
(soft tissue window 30..200 HU), then the largest connected component is kept
and turned into a surface. The reference spleen mask of the dataset is drawn
next to it so the gap between a threshold and an expert label is visible:
this is the honest baseline a learned model has to beat.
"""

from pathlib import Path

import pyvista as pv

import pardesline as pl

HERE = Path(__file__).parent

case = pl.load("msd_task09_spleen").filter(split="Tr")[0]
ct = case.ct
print(ct.info())
soft_tissue = ct.segment(lower=30, upper=200)  # LabelMap, label 1 = foreground
components = soft_tissue.run("simpleitk_segmentation.connected_components", threshold=0.5, min_size=1000)
threshold_surface = components.as_labels().to_mesh(isovalue=0.5)
reference = case.mask.to_mesh(label=1).smooth()

p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1200, 520))
p.subplot(0, 0)
p.add_mesh(ct.to_pyvista().slice("z"), cmap="gray", clim=(-200, 300), show_scalar_bar=False)
p.add_mesh(threshold_surface.to_pyvista(), color="#f0a05a", opacity=0.6, smooth_shading=True)
p.add_text("ct.segment(30, 200 HU) + connected components", font_size=11)
p.subplot(0, 1)
p.add_mesh(ct.to_pyvista().slice("z"), cmap="gray", clim=(-200, 300), show_scalar_bar=False)
p.add_mesh(reference.to_pyvista(), color="#5aa0f0", smooth_shading=True)
p.add_text("reference spleen label (MSD)", font_size=11)
p.link_views()
p.view_isometric()
p.camera.zoom(2.0)
p.screenshot(HERE / "spleen_ct.png")
print("wrote", HERE / "spleen_ct.png")
