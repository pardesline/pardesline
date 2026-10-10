"""Fill holes in a mesh."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Fill holes in mesh")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--hole_size", type=float, default=100.0,
                        help="Maximum hole size to fill")
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    logger.info("Input mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    if mesh.n_cells == 0:
        logger.error("Input has no cells")
        sys.exit(1)

    logger.info("Filling holes with max hole_size={}", args.hole_size)
    result = mesh.fill_holes(args.hole_size)

    logger.info("Saving result mesh to {}", args.output)
    result.save(args.output)

    logger.info("Fill holes (max size={}): {} -> {} cells",
                args.hole_size, mesh.n_cells, result.n_cells)


if __name__ == "__main__":
    main()
