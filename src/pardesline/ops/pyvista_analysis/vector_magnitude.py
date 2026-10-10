"""Compute vector magnitude and store as scalar data."""
import argparse
import sys
import numpy as np
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Compute vector magnitude")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--vector_name", type=str, default="Normals")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        mesh = mesh.extract_surface()

    logger.info("Loaded mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    logger.info("Vector name: '{}'", args.vector_name)

    # If requested vectors don't exist, try normals
    if args.vector_name not in mesh.point_data:
        if args.vector_name == "Normals" and mesh.n_cells > 0:
            logger.info("'Normals' not found, computing point normals")
            mesh = mesh.compute_normals(point_normals=True, cell_normals=False)
        else:
            logger.error("Vector '{}' not found. Available: {}", args.vector_name, list(mesh.point_data.keys()))
            sys.exit(1)

    vectors = mesh.point_data[args.vector_name]
    logger.info("Vector array shape: {}", vectors.shape)

    logger.info("Computing magnitudes via L2 norm")
    magnitudes = np.linalg.norm(vectors, axis=1)
    mesh[f"{args.vector_name}_magnitude"] = magnitudes

    logger.info("Saving output: {}", args.output)
    mesh.save(args.output)

    logger.info("Vector magnitude '{}': min={:.6f}, max={:.6f}, mean={:.6f}, {} points",
                 args.vector_name, magnitudes.min(), magnitudes.max(), magnitudes.mean(), mesh.n_points)


if __name__ == "__main__":
    main()
