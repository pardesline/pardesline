"""Slice a dataset with a plane."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Slice dataset by plane")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--normal_x", type=float, default=1.0)
    parser.add_argument("--normal_y", type=float, default=0.0)
    parser.add_argument("--normal_z", type=float, default=0.0)
    parser.add_argument("--origin_x", type=float, default=None, help="Slice origin x (default: dataset centre)")
    parser.add_argument("--origin_y", type=float, default=None, help="Slice origin y (default: dataset centre)")
    parser.add_argument("--origin_z", type=float, default=None, help="Slice origin z (default: dataset centre)")
    parser.add_argument("--generate_triangles", type=_b, default=False,
                        help="Triangulate the slice output.")
    parser.add_argument("--contour", type=_b, default=False,
                        help="Generate contour edges of the slice.")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)

    normal = (args.normal_x, args.normal_y, args.normal_z)

    # A coordinate not given defaults to the dataset centre; 0 is a coordinate like any other
    # (it used to mean "centre", so a slice through the physical origin was moved).
    origin = tuple(ds.center[i] if v is None else v
                   for i, v in enumerate((args.origin_x, args.origin_y, args.origin_z)))

    logger.info("Slice parameters: normal={}, origin={}", normal, origin)

    logger.info("Applying slice filter")
    result = ds.slice(
        normal=normal,
        origin=origin,
        generate_triangles=args.generate_triangles,
        contour=args.contour,
    )

    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Slice result: {} points, {} cells", result.n_points, result.n_cells)


if __name__ == "__main__":
    main()
