"""Ground removal and object clustering on one KITTI Velodyne sweep.

    pip install "pardesline[local]"
    python examples/kitti_lidar_ground_and_objects/run.py     # writes kitti_objects.png

One sweep (2 MB) is read out of the official 459 MB KITTI raw zip by HTTP
Range; the manifest's layout turns the headerless float32 (N, 4) file into a
point cloud in the sensor frame (metres). ``lidar_scene_detection.object_clustering``
at the catalog defaults removes the ground plane by RANSAC (0.3 m) and clusters
the rest with DBSCAN (0.5 m, 10 points): each colour is one object.
"""

from pathlib import Path

import pyvista as pv

import pardesline as pl

HERE = Path(__file__).parent

drive = pl.load("kitti_raw_2011_09_26_drive_0001")
frame = next(s for s in drive if "lidar" in s.roles)
sweep = frame.lidar  # (N, 4) float32 x, y, z, reflectance -> PointCloud, sensor frame, metres
print(frame.id, sweep.layout, sweep.frame, sweep.units)
objects = sweep.run("lidar_scene_detection.object_clustering")
print(objects.info())

p = pv.Plotter(off_screen=True, window_size=(1200, 600))
cloud = objects.to_pyvista()
p.add_points(
    cloud, scalars="RGB" if "RGB" in cloud.array_names else None, rgb="RGB" in cloud.array_names, point_size=2
)
p.add_text(f"KITTI {frame.id}: ground removed, {cloud.n_points} points clustered into objects", font_size=11)
p.view_xy()
p.camera.zoom(2.2)
p.screenshot(HERE / "kitti_objects.png")
print("wrote", HERE / "kitti_objects.png")
