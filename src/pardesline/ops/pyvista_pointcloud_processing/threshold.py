"""Threshold data by scalar range."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Threshold by scalar range")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--lower", type=float, default=0.0)
    parser.add_argument("--upper", type=float, default=1.0)
    parser.add_argument("--scalars", type=str, default="")
    # Advanced PyVista threshold() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--invert", type=_b, default=False)
    parser.add_argument("--continuous", type=_b, default=False)
    parser.add_argument("--preference", type=str, default="cell", choices=["cell", "point"])
    parser.add_argument("--all_scalars", type=_b, default=False)
    parser.add_argument("--component_mode", type=str, default="all", choices=["all", "any", "component"])
    parser.add_argument("--component", type=int, default=0)
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)

    scalars = args.scalars if args.scalars else None
    logger.info("Parameters: lower={}, upper={}, scalars={}", args.lower, args.upper, scalars)
    logger.info("Advanced: invert={}, continuous={}, preference={}, all_scalars={}, component_mode={}, component={}",
                args.invert, args.continuous, args.preference, args.all_scalars, args.component_mode, args.component)

    if scalars and scalars not in ds.point_data and scalars not in ds.cell_data:
        logger.error("Scalar array '{}' not found. Available: {}",
                      scalars, list(ds.point_data.keys()) + list(ds.cell_data.keys()))
        sys.exit(1)

    # If no scalars exist, add elevation as default
    if not ds.point_data and not ds.cell_data:
        logger.info("No scalar data found, computing implicit distance as default")
        ds = ds.compute_implicit_distance(pv.Plane())
        scalars = "implicit_distance"

    logger.info("Applying threshold filter with range [{}, {}]", args.lower, args.upper)
    result = ds.threshold(
        value=[args.lower, args.upper],
        scalars=scalars,
        invert=args.invert,
        continuous=args.continuous,
        preference=args.preference,
        all_scalars=args.all_scalars,
        component_mode=args.component_mode,
        component=args.component,
    )

    # Convert to PolyData for .ply output
    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Threshold [{}, {}]: {} -> {} points", args.lower, args.upper, ds.n_points, result.n_points)


if __name__ == "__main__":
    main()
