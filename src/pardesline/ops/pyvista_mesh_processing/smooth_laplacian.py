"""Laplacian smoothing of a mesh."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Laplacian mesh smoothing")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--n_iterations", type=int, default=20, help="Smoothing iterations")
    parser.add_argument("--relaxation_factor", type=float, default=0.01, help="Step size")
    # Advanced PyVista smooth() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--convergence", type=float, default=0.0)
    parser.add_argument("--edge_angle", type=float, default=15.0)
    parser.add_argument("--feature_angle", type=float, default=45.0)
    parser.add_argument("--boundary_smoothing", type=_b, default=True)
    parser.add_argument("--feature_smoothing", type=_b, default=False)
    args = parser.parse_args()

    logger.info("Loading input mesh from {}", args.input)
    mesh = pv.read(args.input)
    if not isinstance(mesh, pv.PolyData):
        logger.info("Input is not PolyData, extracting surface")
        mesh = mesh.extract_surface()

    logger.info("Input mesh: {} points, {} cells", mesh.n_points, mesh.n_cells)
    if mesh.n_cells == 0:
        logger.error("Input has no cells to smooth")
        sys.exit(1)

    logger.info("Applying Laplacian smoothing: n_iterations={}, relaxation_factor={}",
                args.n_iterations, args.relaxation_factor)
    logger.info("Advanced: convergence={}, edge_angle={}, feature_angle={}, boundary_smoothing={}, feature_smoothing={}",
                args.convergence, args.edge_angle, args.feature_angle, args.boundary_smoothing, args.feature_smoothing)
    result = mesh.smooth(
        n_iter=args.n_iterations,
        relaxation_factor=args.relaxation_factor,
        convergence=args.convergence,
        edge_angle=args.edge_angle,
        feature_angle=args.feature_angle,
        boundary_smoothing=args.boundary_smoothing,
        feature_smoothing=args.feature_smoothing,
    )

    logger.info("Saving smoothed mesh to {}", args.output)
    result.save(args.output)

    logger.info("Laplacian smooth: {} iterations, relaxation={}, {} points",
                args.n_iterations, args.relaxation_factor, result.n_points)


if __name__ == "__main__":
    main()
