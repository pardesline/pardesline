"""Synthetic data with known answers for the regression tests of the 2026-11 audit.

Everything here is generated in memory from a fixed seed; nothing is downloaded.
Conventions: physical points are (x, y, z) in mm; a registration transform T maps a
FIXED point to the MOVING point where the same anatomy lies, so a moving image built as
``moving(q) = fixed(S(q))`` is registered by ``T = S^-1``.
"""

from __future__ import annotations

import math

import numpy as np

BLOBS = [  # centre as a fraction of the grid (x, y, z), radius fraction, intensity
    (0.31, 0.47, 0.50, 0.125, 100.0),
    (0.62, 0.34, 0.47, 0.094, 60.0),
    (0.53, 0.69, 0.59, 0.078, 140.0),
    (0.47, 0.47, 0.31, 0.062, 80.0),
    (0.70, 0.62, 0.35, 0.050, 120.0),
]


def rotation_z(deg: float) -> np.ndarray:
    t = math.radians(deg)
    return np.array([[math.cos(t), -math.sin(t), 0.0], [math.sin(t), math.cos(t), 0.0], [0.0, 0.0, 1.0]])


def blob_volume(size=(48, 48, 40), spacing=(1.5, 1.5, 2.0), oblique_deg=0.0):
    """Asymmetric Gaussian blobs, grid centre at (0, 0, 0) mm. Returns (image, blob centres in mm)."""
    import SimpleITK as sitk

    n = np.array(size)
    zz, yy, xx = np.meshgrid(*[np.arange(s, dtype=np.float32) for s in size[::-1]], indexing="ij")
    a = np.zeros(xx.shape, np.float32)
    centres = []
    for fx, fy, fz, fr, v in BLOBS:
        c = np.array([fx, fy, fz]) * (n - 1)
        r = fr * n.min()
        a += v * np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2 + (zz - c[2]) ** 2) / (2 * r * r))
        centres.append(c)
    img = sitk.GetImageFromArray(a)
    img.SetSpacing(tuple(float(s) for s in spacing))
    d = rotation_z(oblique_deg)
    img.SetDirection(tuple(d.ravel()))
    img.SetOrigin(tuple(-(d @ (np.array(spacing) * (n - 1) / 2.0))))
    pts = np.array([img.TransformContinuousIndexToPhysicalPoint(tuple(map(float, c))) for c in centres])
    return img, pts


def moved_copy(fixed, s_map):
    """moving(q) = fixed(S(q)), on the fixed grid."""
    import SimpleITK as sitk

    return sitk.Resample(fixed, fixed, s_map, sitk.sitkLinear, 0.0, sitk.sitkFloat32)


def tre(transform, truth, points) -> float:
    """Mean distance between transform(p) and truth(p) over points (mm)."""
    a = np.array([transform.TransformPoint(tuple(map(float, p))) for p in points])
    b = np.array([truth.TransformPoint(tuple(map(float, p))) for p in points])
    return float(np.linalg.norm(a - b, axis=1).mean())


def image_from_array(arr_zyx, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), direction=None):
    import SimpleITK as sitk

    img = sitk.GetImageFromArray(np.ascontiguousarray(arr_zyx))
    img.SetSpacing(tuple(float(s) for s in spacing))
    img.SetOrigin(tuple(float(o) for o in origin))
    if direction is not None:
        img.SetDirection(tuple(float(v) for v in np.asarray(direction).ravel()))
    return img


def ball_mask(shape_zyx, spacing, centres_mm, radius_mm):
    """Union of balls (physical mm, identity direction, origin 0) as a uint8 (z, y, x) array."""
    zz, yy, xx = np.meshgrid(*[np.arange(s) for s in shape_zyx], indexing="ij")
    px, py, pz = xx * spacing[0], yy * spacing[1], zz * spacing[2]
    m = np.zeros(shape_zyx, np.uint8)
    for cx, cy, cz in centres_mm:
        m |= ((px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2 <= radius_mm**2).astype(np.uint8)
    return m


# ----------------------------------------------------------------------------- point clouds
def asym_object_points(n: int, seed: int = 0, feature: float = 1.0) -> np.ndarray:
    """Points on an asymmetric object in mm: box 60 x 40 x 20 + sphere r 12 + cylinder r 5
    (``feature`` scales the sphere and the cylinder: small values give a near-symmetric box)."""
    rng = np.random.default_rng(seed)
    pts = []
    # box surface
    nb = n // 2
    face = rng.integers(0, 6, nb)
    u, v = rng.random(nb), rng.random(nb)
    ext = np.array([60.0, 40.0, 20.0])
    p = (rng.random((nb, 3)) - 0.5) * ext
    ax = face // 2
    sign = np.where(face % 2 == 0, -0.5, 0.5)
    p[np.arange(nb), ax] = sign * ext[ax]
    del u, v
    pts.append(p)
    # sphere on top of one end
    ns = int(n // 4 * feature**2) if feature < 1 else n // 4
    d = rng.normal(size=(ns, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    pts.append(d * 12.0 * feature + np.array([20.0, 5.0, 10.0 + 8.0 * feature]))
    # cylinder sticking out along +y at the other end
    nc = n - nb - ns
    t = rng.random(nc) * 2 * np.pi
    h = rng.random(nc) * 25.0
    pts.append(np.c_[-20.0 + 5.0 * feature * np.cos(t), 20.0 + h * feature, 5.0 * feature * np.sin(t)])
    return np.vstack(pts)


def registration_pair(n: int = 6000, rot_deg=(20.0, -35.0, 120.0), shift=(15.0, -8.0, 5.0),
                      overlap: float = 0.7, noise: float = 0.1, seed: int = 0, feature: float = 1.0):
    """(fixed, moving, T) in mm: two independent samplings of the asymmetric object, the
    moving one cropped to ``overlap`` of its points and moved; T maps moving onto fixed."""
    rng = np.random.default_rng(seed + 1000)
    fixed = asym_object_points(n, seed=seed, feature=feature)
    fixed = fixed + rng.normal(0, noise, fixed.shape)
    m = asym_object_points(n, seed=seed + 1, feature=feature)
    m = m[m[:, 0] <= np.quantile(m[:, 0], overlap)]  # partial overlap
    m = m + rng.normal(0, noise, m.shape)
    r = rot_xyz(*rot_deg)
    moved = m @ r.T + np.asarray(shift)  # moving = R m + s
    t = np.eye(4)
    t[:3, :3], t[:3, 3] = r.T, -r.T @ np.asarray(shift)  # T: moving -> fixed
    return fixed, moved, t


def write_ply(path, points, colors=None, normals=None):
    import open3d as o3d

    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.asarray(points, float)))
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(np.asarray(colors, float))
    if normals is not None:
        pcd.normals = o3d.utility.Vector3dVector(np.asarray(normals, float))
    o3d.io.write_point_cloud(str(path), pcd)
    return path


def pose_error(t_est, t_true) -> tuple[float, float]:
    """(rotation error in degrees, translation error) between two 4x4 transforms."""
    t_est, t_true = np.asarray(t_est), np.asarray(t_true)
    d = t_est @ np.linalg.inv(t_true)
    return rotation_angle_deg(d[:3, :3]), float(np.linalg.norm(t_est[:3, 3] - t_true[:3, 3]))


def rot_xyz(deg_x: float, deg_y: float, deg_z: float) -> np.ndarray:
    ax, ay, az = (math.radians(v) for v in (deg_x, deg_y, deg_z))
    rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    return rz @ ry @ rx


def rotation_angle_deg(r: np.ndarray) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2))))
