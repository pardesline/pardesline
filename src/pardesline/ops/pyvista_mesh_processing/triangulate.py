"""Triangulate all polygonal cells in a mesh."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Triangulate mesh")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    logger.info("Input mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)

    logger.info("Triangulating all polygonal cells")
    result = mesh.triangulate()

    logger.info("Saving triangulated mesh to {}", args.output)
    result.save(args.output)

    logger.info("Triangulated: {} -> {} cells (all triangles)",
                mesh.n_cells, result.n_cells)


if __name__ == "__main__":
    main()
