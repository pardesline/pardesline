"""Extract feature edges from a mesh surface."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Extract feature edges")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--feature_angle", type=float, default=30.0,
                        help="Dihedral angle threshold (degrees)")
    parser.add_argument("--boundary_edges", type=str, default="true",
                        help="Include boundary edges (true/false)")
    parser.add_argument("--non_manifold_edges", type=str, default="true",
                        help="Include non-manifold edges (true/false)")
    parser.add_argument("--manifold_edges", type=str, default="false",
                        help="Include regular manifold edges (true/false)")
    parser.add_argument("--feature_edges", type=_b, default=True,
                        help="Include feature (sharp dihedral-angle) edges.")
    parser.add_argument("--clear_data", type=_b, default=False,
                        help="Drop point/cell data arrays from the output edges.")
    args = parser.parse_args()

    def str_to_bool(s):
        return s.lower() in ("true", "1", "yes")

    logger.info("Loading input: {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        mesh = mesh.extract_surface()

    logger.info("Loaded mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)

    if mesh.n_cells == 0:
        logger.error("Input has no cells for edge extraction")
        sys.exit(1)

    boundary = str_to_bool(args.boundary_edges)
    non_manifold = str_to_bool(args.non_manifold_edges)
    manifold = str_to_bool(args.manifold_edges)

    logger.info("Extracting feature edges: angle={}, boundary={}, non_manifold={}, manifold={}",
                args.feature_angle, boundary, non_manifold, manifold)

    edges = mesh.extract_feature_edges(
        feature_angle=args.feature_angle,
        boundary_edges=boundary,
        feature_edges=args.feature_edges,
        non_manifold_edges=non_manifold,
        manifold_edges=manifold,
        clear_data=args.clear_data,
    )

    logger.info("Extracted {} edge segments ({} points)", edges.n_cells, edges.n_points)

    logger.info("Saving output: {}", args.output)
    edges.save(args.output)

    logger.info("Done: {} edges from {} input faces", edges.n_cells, mesh.n_cells)


if __name__ == "__main__":
    main()
