"""Radial distance: the UNSIGNED distance of each point to the centre of the bounding box
(not the centre of mass, not a signed or surface-to-surface distance), stored as the point
array ``distance_from_center``."""
import argparse
import sys
import numpy as np
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Compute distance field")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        mesh = mesh.extract_surface()

    logger.info("Loaded mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)

    if mesh.n_points == 0:
        logger.error("Input has no points")
        sys.exit(1)

    # Unsigned distance to the bounding-box centre (mesh.center is the bounding-box centre)
    center = mesh.center
    logger.info("Computing distances from the bounding-box centre ({:.3f}, {:.3f}, {:.3f})",
                 center[0], center[1], center[2])
    distances = np.linalg.norm(mesh.points - np.array(center), axis=1)
    mesh["distance_from_center"] = distances

    logger.info("Saving output: {}", args.output)
    mesh.save(args.output)

    logger.info("Distance from center: min={:.6f}, max={:.6f}, {} points",
                 distances.min(), distances.max(), mesh.n_points)


if __name__ == "__main__":
    main()
