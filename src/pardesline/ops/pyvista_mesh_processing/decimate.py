"""Decimate (simplify) a mesh by reducing triangle count."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Decimate mesh using quadric error metrics")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--target_reduction", type=float, default=0.5,
                        help="Fraction of triangles to remove (0-1)")
    # Advanced PyVista decimate() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--volume_preservation", type=_b, default=False)
    parser.add_argument("--attribute_error", type=_b, default=False)
    parser.add_argument("--normals", type=_b, default=False)
    parser.add_argument("--boundary_constraints", type=_b, default=False)
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    n_before = mesh.n_cells
    logger.info("Input mesh: {} points, {} cells", mesh.n_points, n_before)
    if n_before == 0:
        logger.error("Input has no cells to decimate")
        sys.exit(1)

    logger.info("Decimating with target_reduction={:.2f}", args.target_reduction)
    logger.info("Advanced: volume_preservation={}, attribute_error={}, normals={}, boundary_constraints={}",
                args.volume_preservation, args.attribute_error, args.normals, args.boundary_constraints)
    result = mesh.decimate(
        args.target_reduction,
        volume_preservation=args.volume_preservation,
        attribute_error=args.attribute_error,
        normals=args.normals,
        boundary_constraints=args.boundary_constraints,
    )

    logger.info("Saving decimated mesh to {}", args.output)
    result.save(args.output)

    logger.info("Decimated: {} -> {} cells ({:.0f}% target reduction)",
                n_before, result.n_cells, args.target_reduction * 100)


if __name__ == "__main__":
    main()
