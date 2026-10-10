"""Extract isosurface contours from a dataset."""
import argparse
import sys
import numpy as np
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Isosurface contour extraction")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--n_contours", type=int, default=5)
    parser.add_argument("--scalars", type=str, default="")
    parser.add_argument("--compute_normals", type=_b, default=False,
                        help="Compute point normals on the output surface.")
    parser.add_argument("--compute_gradients", type=_b, default=False,
                        help="Compute gradients at the isosurface.")
    parser.add_argument("--compute_scalars", type=_b, default=True,
                        help="Preserve the contoured scalar on the output.")
    parser.add_argument("--method", type=str, default="contour",
                        choices=["contour", "marching_cubes", "flying_edges"],
                        help="Contouring algorithm.")
    parser.add_argument("--preference", type=str, default="point",
                        choices=["point", "cell"],
                        help="Prefer point or cell scalars.")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)

    scalars = args.scalars if args.scalars else None
    logger.info("Parameters: n_contours={}, scalars={}", args.n_contours, scalars)

    # Need scalar data for contouring
    if not ds.point_data and not ds.cell_data:
        logger.error("No scalar data for contouring")
        sys.exit(1)

    if scalars and scalars not in ds.point_data and scalars not in ds.cell_data:
        logger.error("'{}' not found. Available: {}",
                      scalars, list(ds.point_data.keys()) + list(ds.cell_data.keys()))
        sys.exit(1)

    # Contour requires point data -- convert cell data if needed
    if scalars and scalars in ds.cell_data and scalars not in ds.point_data:
        logger.info("Converting cell data '{}' to point data", scalars)
        ds = ds.cell_data_to_point_data()
    elif not ds.point_data and ds.cell_data:
        logger.info("No point data available, converting all cell data to point data")
        ds = ds.cell_data_to_point_data()

    # Compute evenly spaced isovalues
    if scalars:
        arr = ds.point_data.get(scalars)
    else:
        arr = ds.active_scalars
    if arr is None and ds.point_data:
        scalars = list(ds.point_data.keys())[0]
        logger.info("No active scalars, using first available: '{}'", scalars)
        arr = ds.point_data[scalars]
    if arr is None:
        logger.error("No point scalar data available for contouring")
        sys.exit(1)

    vmin, vmax = float(np.nanmin(arr)), float(np.nanmax(arr))
    logger.info("Scalar range: [{:.3f}, {:.3f}]", vmin, vmax)
    isosurfaces = np.linspace(vmin, vmax, args.n_contours + 2)[1:-1].tolist()
    logger.info("Computing {} isosurfaces at values: {}", len(isosurfaces),
                 [f"{v:.3f}" for v in isosurfaces])

    result = ds.contour(
        isosurfaces=isosurfaces,
        scalars=scalars,
        compute_normals=args.compute_normals,
        compute_gradients=args.compute_gradients,
        compute_scalars=args.compute_scalars,
        method=args.method,
        preference=args.preference,
    )

    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Contour: {} isosurfaces in [{:.3f}, {:.3f}], {} points, {} cells",
                 args.n_contours, vmin, vmax, result.n_points, result.n_cells)


if __name__ == "__main__":
    main()
