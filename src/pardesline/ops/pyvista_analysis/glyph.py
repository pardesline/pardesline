"""Generate glyphs (arrows) from vector data on a mesh."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Generate glyph arrows from vectors")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scale_factor", type=float, default=0.01)
    parser.add_argument("--vector_name", type=str, default="Normals")
    parser.add_argument("--scale", type=_b, default=False,
                        help="Scale glyphs by scalar/vector magnitude.")
    parser.add_argument("--tolerance", type=float, default=-1.0,
                        help="Merge tolerance as fraction of bbox (-1 = auto/None).")
    parser.add_argument("--absolute", type=_b, default=False,
                        help="Interpret tolerance as an absolute distance.")
    parser.add_argument("--clamping", type=_b, default=False,
                        help="Clamp glyph scaling to the rng range.")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        mesh = mesh.extract_surface()

    logger.info("Loaded mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    logger.info("Parameters: vector_name='{}', scale_factor={}", args.vector_name, args.scale_factor)

    # If requested vectors don't exist, try to compute normals
    if args.vector_name not in mesh.point_data:
        if args.vector_name == "Normals" and mesh.n_cells > 0:
            logger.info("'Normals' not found, computing point normals")
            mesh = mesh.compute_normals(point_normals=True, cell_normals=False)
        else:
            available = list(mesh.point_data.keys())
            logger.error("Vector '{}' not found. Available: {}", args.vector_name, available)
            sys.exit(1)

    logger.info("Generating glyphs from '{}' with scale_factor={}", args.vector_name, args.scale_factor)
    tolerance = None if args.tolerance is None or args.tolerance < 0 else args.tolerance
    result = mesh.glyph(
        orient=args.vector_name,
        scale=args.scale,
        factor=args.scale_factor,
        tolerance=tolerance,
        absolute=args.absolute,
        clamping=args.clamping,
    )

    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Glyphs from '{}' (factor={}): {} points, {} cells",
                 args.vector_name, args.scale_factor, result.n_points, result.n_cells)


if __name__ == "__main__":
    main()
