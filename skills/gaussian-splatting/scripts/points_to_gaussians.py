"""Initialise 3D Gaussians from a point cloud and write a 3DGS-compatible PLY.

Per point: mean = position; scale = log(mean distance to the k nearest
neighbours) on the three axes; rotation = identity quaternion; opacity =
logit(alpha0); colour = SH degree-0 from RGB (f_dc = (rgb - 0.5) / C0), all
f_rest = 0. The output opens in gsplat, the reference implementation, Nerfstudio
viewers and the web viewers on huggingface.co.

    python points_to_gaussians.py cloud.ply splat.ply
    python points_to_gaussians.py cloud.ply splat.ply --k 3 --alpha 0.1 --colour 0.8 0.7 0.6 --sh-degree 3

Only NumPy and SciPy are needed; pardesline reads the input (any point cloud or
mesh file, raw arrays with --layout).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

C0 = 0.28209479177387814  # SH degree-0 basis constant


def gaussians_from_points(
    xyz: np.ndarray, rgb: np.ndarray | None, *, k: int = 3, alpha0: float = 0.1, sh_degree: int = 3
) -> dict[str, np.ndarray]:
    from scipy.spatial import cKDTree

    n = len(xyz)
    dist, _ = cKDTree(xyz).query(xyz, k=k + 1)  # the first neighbour is the point itself
    mean_nn = dist[:, 1:].mean(axis=1)
    mean_nn = np.maximum(mean_nn, 1e-7)
    log_scale = np.log(mean_nn).astype(np.float32)
    scales = np.repeat(log_scale[:, None], 3, axis=1)
    rots = np.tile(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), (n, 1))
    opacity = np.full((n, 1), math.log(alpha0 / (1 - alpha0)), dtype=np.float32)
    if rgb is None:
        rgb = np.full((n, 3), 0.5, dtype=np.float32)
    rgb = np.asarray(rgb, dtype=np.float32)
    if rgb.max() > 1.0:
        rgb = rgb / 255.0
    f_dc = ((rgb - 0.5) / C0).astype(np.float32)
    n_rest = 3 * ((sh_degree + 1) ** 2 - 1)
    f_rest = np.zeros((n, n_rest), dtype=np.float32)
    return {
        "xyz": xyz.astype(np.float32),
        "normals": np.zeros((n, 3), dtype=np.float32),
        "f_dc": f_dc,
        "f_rest": f_rest,
        "opacity": opacity,
        "scale": scales,
        "rot": rots,
    }


def write_splat_ply(path: str | Path, g: dict[str, np.ndarray]) -> Path:
    n = len(g["xyz"])
    names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"]
    names += [f"f_rest_{i}" for i in range(g["f_rest"].shape[1])]
    names += ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    data = np.concatenate(
        [g["xyz"], g["normals"], g["f_dc"], g["f_rest"], g["opacity"], g["scale"], g["rot"]], axis=1
    ).astype("<f4")
    assert data.shape[1] == len(names)
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {n}"]
    header += [f"property float {name}" for name in names]
    header.append("end_header")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fp:
        fp.write(("\n".join(header) + "\n").encode("ascii"))
        fp.write(np.ascontiguousarray(data).tobytes())
    return out


def read_splat_ply(path: str | Path) -> dict[str, np.ndarray]:
    """Read a 3DGS PLY back (means, opacity, scales, rotations, SH dc)."""
    with open(path, "rb") as fp:
        header = []
        while True:
            line = fp.readline().decode("ascii").strip()
            header.append(line)
            if line == "end_header":
                break
        n = int(next(h for h in header if h.startswith("element vertex")).split()[-1])
        props = [h.split()[-1] for h in header if h.startswith("property")]
        arr = np.frombuffer(fp.read(n * len(props) * 4), dtype="<f4").reshape(n, len(props))
    col = {p: i for i, p in enumerate(props)}
    out = {
        "xyz": arr[:, [col["x"], col["y"], col["z"]]],
        "opacity": 1 / (1 + np.exp(-arr[:, col["opacity"]])),
        "scale": np.exp(arr[:, [col["scale_0"], col["scale_1"], col["scale_2"]]]),
        "rot": arr[:, [col["rot_0"], col["rot_1"], col["rot_2"], col["rot_3"]]],
        "rgb": np.clip(arr[:, [col["f_dc_0"], col["f_dc_1"], col["f_dc_2"]]] * C0 + 0.5, 0, 1),
    }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="point cloud / mesh file, or a bundled pardesline dataset name")
    ap.add_argument("output", help="3DGS .ply to write")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--alpha", type=float, default=0.1, help="initial opacity")
    ap.add_argument("--sh-degree", type=int, default=3, choices=[0, 1, 2, 3])
    ap.add_argument("--colour", type=float, nargs=3, help="uniform RGB in 0-1 when the cloud has none")
    ap.add_argument("--layout", help="JSON layout for raw .npy/.bin inputs")
    ap.add_argument("--num-points", type=int, default=100000, help="points sampled from a mesh input")
    args = ap.parse_args()

    import pardesline as pl

    src = pl.load(args.input, layout=json.loads(args.layout) if args.layout else None)
    if isinstance(src, pl.Dataset):
        src = next(iter(src.meshes), None) or next(iter(src.points))
    if src.kind == "mesh":
        src = src.to_points(num_points=args.num_points)
    geo = src.to_open3d() if not src.is_raw_array else None
    if geo is not None and hasattr(geo, "points"):
        xyz = np.asarray(geo.points)
        rgb = np.asarray(geo.colors) if len(geo.colors) == len(geo.points) else None
    else:
        xyz = src.to_numpy()
        rgb = None
    if args.colour:
        rgb = np.tile(np.array(args.colour, dtype=np.float32), (len(xyz), 1))
    g = gaussians_from_points(xyz, rgb, k=args.k, alpha0=args.alpha, sh_degree=args.sh_degree)
    out = write_splat_ply(args.output, g)
    back = read_splat_ply(out)
    print(
        json.dumps(
            {
                "gaussians": len(xyz),
                "file_mb": round(out.stat().st_size / 1e6, 2),
                "floats_per_gaussian": int(11 + 3 + g["f_rest"].shape[1] + 3),
                "median_scale": float(np.median(back["scale"])),
                "opacity": float(back["opacity"][0]),
                "frame": src.frame.describe(),
                "output": str(out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
