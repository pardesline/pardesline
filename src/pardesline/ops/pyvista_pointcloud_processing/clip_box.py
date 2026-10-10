"""Clip data by an axis-aligned bounding box."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Clip by bounding box")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--x_min", type=float, default=-0.5)
    parser.add_argument("--x_max", type=float, default=0.5)
    parser.add_argument("--y_min", type=float, default=-0.5)
    parser.add_argument("--y_max", type=float, default=0.5)
    parser.add_argument("--z_min", type=float, default=-0.5)
    parser.add_argument("--z_max", type=float, default=0.5)
    # Advanced PyVista clip_box() knobs. NOTE: invert defaults to False here to match
    # the script's original hardcoded invert=False (PyVista's own default is True).
    parser.add_argument("--invert", type=_b, default=False)
    parser.add_argument("--merge_points", type=_b, default=True)
    parser.add_argument("--crinkle", type=_b, default=False)
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)

    bounds = [args.x_min, args.x_max, args.y_min, args.y_max, args.z_min, args.z_max]
    logger.info("Clip box bounds: {}", bounds)
    logger.info("Advanced: invert={}, merge_points={}, crinkle={}", args.invert, args.merge_points, args.crinkle)

    logger.info("Applying clip_box filter (invert={})", args.invert)
    result = ds.clip_box(bounds, invert=args.invert, merge_points=args.merge_points, crinkle=args.crinkle)

    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Clipped by box: {} -> {} points", ds.n_points, result.n_points)


if __name__ == "__main__":
    main()
