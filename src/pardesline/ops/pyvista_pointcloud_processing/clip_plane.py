"""Clip data by a plane."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Clip by plane")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--origin_x", type=float, default=None, help="Plane origin x (default: dataset centre)")
    parser.add_argument("--origin_y", type=float, default=None, help="Plane origin y (default: dataset centre)")
    parser.add_argument("--origin_z", type=float, default=None, help="Plane origin z (default: dataset centre)")
    parser.add_argument("--normal_x", type=float, default=1.0)
    parser.add_argument("--normal_y", type=float, default=0.0)
    parser.add_argument("--normal_z", type=float, default=0.0)
    # Advanced PyVista clip() knobs (defaults == PyVista defaults -> no behavior change)
    parser.add_argument("--invert", type=_b, default=True)
    parser.add_argument("--value", type=float, default=0.0)
    parser.add_argument("--crinkle", type=_b, default=False)
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)

    origin = tuple(ds.center[i] if v is None else v for i, v in enumerate((args.origin_x, args.origin_y, args.origin_z)))
    normal = (args.normal_x, args.normal_y, args.normal_z)
    logger.info("Clip plane parameters: origin={}, normal={}", origin, normal)
    logger.info("Advanced: invert={}, value={}, crinkle={}", args.invert, args.value, args.crinkle)

    logger.info("Applying clip filter")
    result = ds.clip(normal=normal, origin=origin, invert=args.invert, value=args.value, crinkle=args.crinkle)

    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    if result.n_points == 0:
        logger.error("The clip kept no point (origin {}, normal {}, invert {}); data bounds are {}",
                     origin, normal, args.invert, list(ds.bounds))
        sys.exit(1)
    result.save(args.output)
    logger.info("Clipped by plane: {} -> {} points", ds.n_points, result.n_points)


if __name__ == "__main__":
    main()
