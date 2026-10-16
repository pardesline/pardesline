"""Point cloud to 3D Gaussian splats on the Stanford bunny.

    pip install "pardesline[local]"
    python examples/points_to_gaussians_bunny/run.py        # writes bunny_splats.ply (opens in gsplat, Nerfstudio and the Hugging Face viewers)

Runs the reference script of the ``gaussian-splatting`` skill: the bunny
mesh is sampled into points, each point becomes a Gaussian (scale from the
k-nearest-neighbour distance, identity rotation, SH degree-0 colour) and the
result is written as a 3DGS-compatible PLY.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

import pardesline as pl

HERE = Path(__file__).parent
points = pl.load("open3d_bunny")[0].mesh.to_points(num_points=50000, seed=1)
run(
    "gaussian-splatting",
    "points_to_gaussians.py",
    str(points.path),
    str(HERE / "bunny_splats.ply"),
    "--k",
    "4",
)

# Preview: the Gaussian centres coloured by height (a splat viewer renders the ellipsoids properly).
import pyvista as pv

centres = pl.load(
    HERE / "bunny_splats.ply"
).to_numpy()  # the PLY opens as a point cloud: x, y, z are standard
p = pv.Plotter(off_screen=True, window_size=(900, 600))
p.add_points(pv.PolyData(centres), scalars=centres[:, 1], cmap="magma", point_size=3, show_scalar_bar=False)
p.add_text(f"{len(centres)} Gaussians initialised from the bunny points (k = 4 neighbours)", font_size=11)
p.camera_position = "xy"
p.camera.elevation = 20
p.screenshot(HERE / "bunny_splats.png")
print("wrote", HERE / "bunny_splats.png")
