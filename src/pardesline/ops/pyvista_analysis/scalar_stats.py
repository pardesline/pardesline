"""Compute scalar statistics and add a normalized scalar field."""
import argparse
import sys
import numpy as np
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Scalar statistics and normalization")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scalars", type=str, default="")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        mesh = mesh.extract_surface()

    logger.info("Loaded mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)

    # Find scalar array
    scalars_name = args.scalars if args.scalars else None
    if not scalars_name:
        if mesh.point_data:
            scalars_name = list(mesh.point_data.keys())[0]
            logger.info("No scalars specified, using first available: '{}'", scalars_name)
        elif mesh.n_points > 0:
            # Use Z-coordinate as default scalar
            logger.info("No point data available, using Z-coordinate as 'elevation'")
            mesh["elevation"] = mesh.points[:, 2]
            scalars_name = "elevation"
        else:
            logger.error("No data available")
            sys.exit(1)

    if scalars_name not in mesh.point_data:
        logger.error("'{}' not found. Available: {}", scalars_name, list(mesh.point_data.keys()))
        sys.exit(1)

    arr = mesh.point_data[scalars_name]
    logger.info("Computing statistics for '{}' ({} values)", scalars_name, len(arr))

    vmin = float(np.nanmin(arr))
    vmax = float(np.nanmax(arr))
    vmean = float(np.nanmean(arr))
    vmedian = float(np.nanmedian(arr))
    vstd = float(np.nanstd(arr))

    logger.info("Statistics: min={:.6f}, max={:.6f}, mean={:.6f}, median={:.6f}, std={:.6f}",
                 vmin, vmax, vmean, vmedian, vstd)

    # Add normalized version
    if vmax - vmin > 1e-12:
        logger.info("Normalizing to [0, 1] range (range={:.6f})", vmax - vmin)
        normalized = (arr - vmin) / (vmax - vmin)
    else:
        logger.info("Scalar range too small ({:.2e}), setting normalized values to zero", vmax - vmin)
        normalized = np.zeros_like(arr)
    mesh[f"{scalars_name}_normalized"] = normalized

    logger.info("Saving output: {}", args.output)
    mesh.save(args.output)

    logger.info("Scalar stats for '{}': min={:.6f}, max={:.6f}", scalars_name, vmin, vmax)
    logger.info("  mean={:.6f}, median={:.6f}, std={:.6f}", vmean, vmedian, vstd)
    logger.info("  Added '{}_normalized' field, {} points", scalars_name, mesh.n_points)


if __name__ == "__main__":
    main()
