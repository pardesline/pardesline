"""Create three orthogonal slices through a dataset."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Orthogonal slices")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--x", type=float, default=0.0, help="X position for YZ slice")
    parser.add_argument("--y", type=float, default=0.0, help="Y position for XZ slice")
    parser.add_argument("--z", type=float, default=0.0, help="Z position for XY slice")
    parser.add_argument("--generate_triangles", type=_b, default=False,
                        help="Triangulate the slice output.")
    parser.add_argument("--contour", type=_b, default=False,
                        help="Generate contour edges of the slices.")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)

    center = ds.center
    logger.info("Dataset center: ({:.3f}, {:.3f}, {:.3f})", center[0], center[1], center[2])

    # Use center if position is 0
    x = args.x if args.x != 0.0 else center[0]
    y = args.y if args.y != 0.0 else center[1]
    z = args.z if args.z != 0.0 else center[2]
    logger.info("Slice positions: x={:.3f}, y={:.3f}, z={:.3f}", x, y, z)

    logger.info("Computing orthogonal slices")
    result = ds.slice_orthogonal(
        x=x, y=y, z=z,
        generate_triangles=args.generate_triangles,
        contour=args.contour,
    )

    # MultiBlock -> merge into single PolyData
    if isinstance(result, pv.MultiBlock):
        logger.info("Merging {} blocks into single PolyData", result.n_blocks)
        combined = pv.PolyData()
        for i in range(result.n_blocks):
            block = result[i]
            if block is not None and block.n_points > 0:
                if not isinstance(block, pv.PolyData):
                    block = block.extract_surface()
                combined = combined.merge(block)
        result = combined

    result.save(args.output)
    logger.info("Orthogonal slices at ({:.3f}, {:.3f}, {:.3f}): {} points, {} cells",
                 x, y, z, result.n_points, result.n_cells)


if __name__ == "__main__":
    main()
