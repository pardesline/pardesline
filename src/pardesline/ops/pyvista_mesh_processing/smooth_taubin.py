"""Taubin smoothing of a mesh (volume-preserving)."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Taubin mesh smoothing")
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output mesh file")
    parser.add_argument("--n_iterations", type=int, default=20, help="Smoothing iterations")
    parser.add_argument("--pass_band", type=float, default=0.1, help="Pass-band value")
    # Advanced PyVista smooth_taubin() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--edge_angle", type=float, default=15.0)
    parser.add_argument("--feature_angle", type=float, default=45.0)
    parser.add_argument("--boundary_smoothing", type=_b, default=True)
    parser.add_argument("--feature_smoothing", type=_b, default=False)
    parser.add_argument("--non_manifold_smoothing", type=_b, default=False)
    parser.add_argument("--normalize_coordinates", type=_b, default=False)
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

    logger.info("Applying Taubin smoothing: n_iterations={}, pass_band={}",
                args.n_iterations, args.pass_band)
    logger.info("Advanced: edge_angle={}, feature_angle={}, boundary_smoothing={}, feature_smoothing={}, "
                "non_manifold_smoothing={}, normalize_coordinates={}",
                args.edge_angle, args.feature_angle, args.boundary_smoothing, args.feature_smoothing,
                args.non_manifold_smoothing, args.normalize_coordinates)
    result = mesh.smooth_taubin(
        n_iter=args.n_iterations,
        pass_band=args.pass_band,
        edge_angle=args.edge_angle,
        feature_angle=args.feature_angle,
        boundary_smoothing=args.boundary_smoothing,
        feature_smoothing=args.feature_smoothing,
        non_manifold_smoothing=args.non_manifold_smoothing,
        normalize_coordinates=args.normalize_coordinates,
    )

    logger.info("Saving smoothed mesh to {}", args.output)
    result.save(args.output)

    logger.info("Taubin smooth: {} iterations, pass_band={}, {} points",
                args.n_iterations, args.pass_band, result.n_points)


if __name__ == "__main__":
    main()
