"""Extract points whose scalar values lie within a range."""
import argparse
import sys
import numpy as np
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Extract points by scalar range")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scalars", type=str, default="")
    parser.add_argument("--lower", type=float, default=0.0)
    parser.add_argument("--upper", type=float, default=1.0)
    # Advanced PyVista extract_points() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--adjacent_cells", type=_b, default=True)
    parser.add_argument("--include_cells", type=_b, default=True)
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    if not isinstance(ds, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        ds = ds.extract_surface()

    logger.info("Loaded dataset: {} points", ds.n_points)

    scalars_name = args.scalars if args.scalars else None
    logger.info("Parameters: scalars={}, lower={}, upper={}", scalars_name, args.lower, args.upper)

    # If no scalars specified and none exist, use Z coordinate
    if not scalars_name and not ds.point_data:
        logger.info("No scalar data found, using Z coordinate as 'elevation'")
        ds["elevation"] = ds.points[:, 2]
        scalars_name = "elevation"

    if scalars_name:
        if scalars_name not in ds.point_data:
            logger.error("'{}' not found. Available: {}", scalars_name, list(ds.point_data.keys()))
            sys.exit(1)
        arr = ds.point_data[scalars_name]
    else:
        arr = ds.active_scalars
        if arr is None:
            logger.error("No scalar data available")
            sys.exit(1)

    logger.info("Scalar range in data: min={:.6f}, max={:.6f}", float(arr.min()), float(arr.max()))
    mask = (arr >= args.lower) & (arr <= args.upper)
    indices = np.where(mask)[0]
    logger.info("Points matching range [{}, {}]: {}/{}", args.lower, args.upper, len(indices), ds.n_points)

    logger.info("Extracting matched points (adjacent_cells={}, include_cells={})",
                args.adjacent_cells, args.include_cells)
    result = ds.extract_points(indices, adjacent_cells=args.adjacent_cells, include_cells=args.include_cells)
    if not isinstance(result, pv.PolyData):
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Extracted points [{}, {}]: {} -> {} points", args.lower, args.upper, ds.n_points, result.n_points)


if __name__ == "__main__":
    main()
