"""<Method name>: one line on what it does and which library it calls.

python -m pardesline.ops.<module>.my_method --input in.ply --output out.ply --radius 0.05
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from loguru import logger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="Input file (.ply, .pcd ...)")
    p.add_argument("--output", required=True, help="Output file; the extension must match the catalog")
    # one flag per catalog parameter, same name, same default
    p.add_argument("--radius", type=float, default=0.05, help="Neighbourhood radius in file units")
    p.add_argument("--max_nn", type=int, default=30, help="Maximum neighbours")
    return p.parse_args(argv)


def run(input_path: Path, output_path: Path, *, radius: float, max_nn: int) -> dict:
    """The algorithm. Import the native library here, not at module level."""
    import open3d as o3d

    cloud = o3d.io.read_point_cloud(str(input_path))
    if not cloud.has_points():
        raise ValueError(f"{input_path}: no points read")
    logger.info("PROGRESS 10")
    cloud.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn))
    logger.info("PROGRESS 90")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    o3d.io.write_point_cloud(str(output_path), cloud)
    return {"points": len(cloud.points), "radius": radius, "max_nn": max_nn}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run(Path(args.input), Path(args.output), radius=args.radius, max_nn=args.max_nn)
    except Exception as exc:
        logger.error("{}", exc)
        return 1
    Path(str(args.output) + ".json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    logger.info("PROGRESS 100")
    return 0


if __name__ == "__main__":
    sys.exit(main())
