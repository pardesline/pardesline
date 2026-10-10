"""Subdivide a mesh to increase resolution."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Subdivide mesh")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--n_subdivisions", type=int, default=1, help="Number of iterations")
    parser.add_argument("--algorithm", type=str, default="linear",
                        help="Algorithm: linear, butterfly, or loop")
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    logger.info("Input mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    if mesh.n_cells == 0:
        logger.error("Input has no cells to subdivide")
        sys.exit(1)

    logger.info("Subdividing with algorithm='{}', n_subdivisions={}", args.algorithm, args.n_subdivisions)
    result = mesh.subdivide(args.n_subdivisions, subfilter=args.algorithm)

    logger.info("Saving subdivided mesh to {}", args.output)
    result.save(args.output)

    logger.info("Subdivided ({}, {}x): {} -> {} cells",
                args.algorithm, args.n_subdivisions, mesh.n_cells, result.n_cells)


if __name__ == "__main__":
    main()
