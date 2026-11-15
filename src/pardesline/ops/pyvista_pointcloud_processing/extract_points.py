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
    parser.add_argument("--scalars", type=str, default="", help="Point array to test (required)")
    parser.add_argument("--lower", type=float, default=None, help="Lower bound (required)")
    parser.add_argument("--upper", type=float, default=None, help="Upper bound (required)")
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

    if not scalars_name:
        logger.error("--scalars is required (available point arrays: {}); use 'elevation' for the z coordinate",
                     list(ds.point_data.keys()))
        sys.exit(1)
    if scalars_name == "elevation" and "elevation" not in ds.point_data:
        ds["elevation"] = ds.points[:, 2]

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
    if args.lower is None or args.upper is None:
        logger.error("--lower and --upper are required; '{}' ranges from {} to {}", scalars_name,
                     float(arr.min()), float(arr.max()))
        sys.exit(1)
    mask = (arr >= args.lower) & (arr <= args.upper)
    indices = np.where(mask)[0]
    if len(indices) == 0:
        logger.error("No point has '{}' in [{}, {}]", scalars_name, args.lower, args.upper)
        sys.exit(1)
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
