"""Atlas label transfer on the Stanford bunny: register a labelled atlas, transfer labels, evaluate.

    pip install "pardesline[local]"
    python examples/atlas_label_transfer_bunny/run.py       # writes ./out/ with the labelled scan and a JSON report

Runs the reference script of the ``atlas-label-transfer`` skill. The bunny
(Open3D data) is the atlas, labelled into head / ears / body / base; the
"scan" is a rotated, noisy, sub-sampled copy with a known transform, so the
label agreement after RANSAC + ICP registration and nearest-structure transfer
is measured exactly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

HERE = Path(__file__).parent
run("atlas-label-transfer", "atlas_label_transfer.py", "--out", str(HERE / "out"))

# Render the transferred labels: one colour per structure, the atlas in grey behind.
import pyvista as pv

colours = {"head": "#f0a05a", "ears": "#5aa0f0", "body": "#8fd18f", "base": "#d18fd1"}
p = pv.Plotter(off_screen=True, window_size=(900, 600))
p.add_points(pv.read(HERE / "out" / "atlas.ply"), color="#444a55", point_size=2)
for name, colour in colours.items():
    p.add_points(pv.read(HERE / "out" / f"scan_{name}.ply"), color=colour, point_size=4, label=name)
p.add_legend()
p.add_text("Atlas (grey) and the scan labelled by transfer", font_size=11)
p.camera_position = "xy"
p.camera.elevation = 20
p.screenshot(HERE / "atlas_transfer.png")
print("wrote", HERE / "atlas_transfer.png")
