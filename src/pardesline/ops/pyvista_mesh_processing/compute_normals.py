"""Compute point and cell normals for a mesh."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Compute mesh normals")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--flip_normals", type=int, default=0, help="Flip normals (0/1)")
    parser.add_argument("--consistency", type=int, default=1,
                        help="Enforce consistent orientation (0/1)")
    # Advanced PyVista compute_normals() knobs. cell_normals / point_normals default True
    # to match the script's original hardcoded values; the rest == PyVista defaults.
    parser.add_argument("--cell_normals", type=_b, default=True)
    parser.add_argument("--point_normals", type=_b, default=True)
    parser.add_argument("--split_vertices", type=_b, default=False)
    parser.add_argument("--auto_orient_normals", type=_b, default=False)
    parser.add_argument("--non_manifold_traversal", type=_b, default=True)
    parser.add_argument("--feature_angle", type=float, default=30.0)
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    logger.info("Input mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    if mesh.n_cells == 0:
        logger.error("Input has no cells for normal computation")
        sys.exit(1)

    logger.info("Computing normals: flip_normals={}, consistent_normals={}",
                bool(args.flip_normals), bool(args.consistency))
    logger.info("Advanced: cell_normals={}, point_normals={}, split_vertices={}, auto_orient_normals={}, "
                "non_manifold_traversal={}, feature_angle={}",
                args.cell_normals, args.point_normals, args.split_vertices, args.auto_orient_normals,
                args.non_manifold_traversal, args.feature_angle)
    result = mesh.compute_normals(
        cell_normals=args.cell_normals,
        point_normals=args.point_normals,
        split_vertices=args.split_vertices,
        flip_normals=bool(args.flip_normals),
        consistent_normals=bool(args.consistency),
        auto_orient_normals=args.auto_orient_normals,
        non_manifold_traversal=args.non_manifold_traversal,
        feature_angle=args.feature_angle,
    )

    logger.info("Saving mesh with normals to {}", args.output)
    result.save(args.output)

    has_pn = "Normals" in result.point_data
    has_cn = "Normals" in result.cell_data
    logger.info("Normals computed: point_normals={}, cell_normals={}, {} points",
                has_pn, has_cn, result.n_points)


if __name__ == "__main__":
    main()
