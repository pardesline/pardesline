"""Threshold a volume by scalar range, preserving volumetric structure."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Volume threshold")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--lower", type=float, default=0.0)
    parser.add_argument("--upper", type=float, default=1.0)
    parser.add_argument("--scalars", type=str, default="",
                        help="Scalar array name (empty = active scalars).")
    parser.add_argument("--invert", type=_b, default=False,
                        help="Invert the threshold selection.")
    parser.add_argument("--continuous", type=_b, default=False,
                        help="Use continuous cell range for thresholding.")
    parser.add_argument("--preference", type=str, default="cell",
                        choices=["cell", "point"],
                        help="Prefer cell or point scalars.")
    parser.add_argument("--all_scalars", type=_b, default=False,
                        help="Require all scalar components to satisfy the range.")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)
    logger.info("Parameters: lower={}, upper={}", args.lower, args.upper)

    if not ds.point_data and not ds.cell_data:
        logger.error("No scalar data for thresholding")
        sys.exit(1)

    logger.info("Available point data: {}", list(ds.point_data.keys()))
    logger.info("Available cell data: {}", list(ds.cell_data.keys()))

    scalars = args.scalars if args.scalars else None
    logger.info("Applying volume threshold filter [{}, {}]", args.lower, args.upper)
    result = ds.threshold(
        value=[args.lower, args.upper],
        scalars=scalars,
        invert=args.invert,
        continuous=args.continuous,
        preference=args.preference,
        all_scalars=args.all_scalars,
    )

    # Save as VTU to preserve volumetric structure
    if isinstance(result, pv.UnstructuredGrid):
        logger.info("Result is UnstructuredGrid, saving directly")
        result.save(args.output)
    else:
        logger.info("Casting result to UnstructuredGrid before saving")
        result.cast_to_unstructured_grid().save(args.output)

    logger.info("Volume threshold [{}, {}]: {} -> {} cells", args.lower, args.upper, ds.n_cells, result.n_cells)


if __name__ == "__main__":
    main()
