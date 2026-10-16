"""Poisson surface reconstruction of the Stanford bunny from a sampled point cloud.

    pip install "pardesline[local]"
    python examples/poisson_reconstruction_bunny/run.py      # writes bunny_poisson.png and bunny_poisson.ply

The bunny mesh (Open3D data) is sampled into 20 000 points (Poisson-disk),
the points are cleaned (statistical outlier removal) and a surface is rebuilt
with ``to_mesh()`` = ``point_cloud_reconstruction.poisson`` at the catalog
defaults (octree depth 9, density-trimmed at the 1 % quantile so the surface
does not balloon where there are no points). The result is a clean surface,
not a closed one: Poisson is lossy and parametric, and the sidecar says so.
"""

from pathlib import Path

import pyvista as pv

import pardesline as pl

HERE = Path(__file__).parent

mesh = pl.load("open3d_bunny")[0].mesh
points = mesh.to_points(num_points=20000, seed=1).clean()
surface = points.to_mesh()  # Poisson, depth 9, density_quantile 0.01
surface.save(HERE / "bunny_poisson.ply")
print(mesh.info(), "->", points.info(), "->", surface.info())

p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1200, 520))
p.subplot(0, 0)
p.add_points(points.to_pyvista(), color="#8fa3bf", point_size=2)
p.add_text("20 000 points (Poisson-disk, cleaned)", font_size=11)
p.subplot(0, 1)
p.add_mesh(surface.to_pyvista(), color="#f0a05a", smooth_shading=True)
p.add_text("points.to_mesh(): Poisson, density-trimmed", font_size=11)
p.link_views()
p.camera_position = "xy"
p.camera.elevation = 20
p.screenshot(HERE / "bunny_poisson.png")
print("wrote", HERE / "bunny_poisson.png")
