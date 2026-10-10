"""Clean a mesh: merge duplicates, remove degenerates."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Clean mesh")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--tolerance", type=float, default=0.0,
                        help="Point merge tolerance (0 = exact duplicates only)")
    # Advanced PyVista clean() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--point_merging", type=_b, default=True)
    parser.add_argument("--absolute", type=_b, default=True)
    parser.add_argument("--lines_to_points", type=_b, default=True)
    parser.add_argument("--polys_to_lines", type=_b, default=True)
    parser.add_argument("--strips_to_polys", type=_b, default=True)
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    n_before = mesh.n_points
    logger.info("Input mesh: {} points, {} cells", n_before, mesh.n_cells)
    logger.info("Advanced: point_merging={}, absolute={}, lines_to_points={}, polys_to_lines={}, strips_to_polys={}",
                args.point_merging, args.absolute, args.lines_to_points, args.polys_to_lines, args.strips_to_polys)

    clean_kwargs = dict(
        point_merging=args.point_merging,
        absolute=args.absolute,
        lines_to_points=args.lines_to_points,
        polys_to_lines=args.polys_to_lines,
        strips_to_polys=args.strips_to_polys,
    )

    if args.tolerance > 0:
        logger.info("Cleaning with merge tolerance={}", args.tolerance)
        result = mesh.clean(tolerance=args.tolerance, **clean_kwargs)
    else:
        logger.info("Cleaning with exact duplicate merging (tolerance=0)")
        result = mesh.clean(**clean_kwargs)

    logger.info("Saving cleaned mesh to {}", args.output)
    result.save(args.output)

    logger.info("Cleaned: {} -> {} points, {} cells",
                n_before, result.n_points, result.n_cells)


if __name__ == "__main__":
    main()
