"""Compute surface curvature and store as scalar data."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Compute surface curvature")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--curvature_type", type=str, default="mean",
                        help="mean, gaussian, maximum, or minimum")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        mesh = mesh.extract_surface()

    logger.info("Loaded mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    logger.info("Curvature type: {}", args.curvature_type)

    if mesh.n_cells == 0:
        logger.error("Input has no cells for curvature computation")
        sys.exit(1)

    valid_types = ["mean", "gaussian", "maximum", "minimum"]
    if args.curvature_type not in valid_types:
        logger.error("Invalid curvature type '{}'. Options: {}", args.curvature_type, valid_types)
        sys.exit(1)

    logger.info("Computing {} curvature", args.curvature_type)
    curv_arr = mesh.curvature(curv_type=args.curvature_type)
    mesh[f"curvature_{args.curvature_type}"] = curv_arr

    logger.info("Saving output: {}", args.output)
    mesh.save(args.output)

    logger.info("Curvature ({}): min={:.6f}, max={:.6f}, mean={:.6f}, {} points",
                 args.curvature_type, curv_arr.min(), curv_arr.max(), curv_arr.mean(), mesh.n_points)


if __name__ == "__main__":
    main()
