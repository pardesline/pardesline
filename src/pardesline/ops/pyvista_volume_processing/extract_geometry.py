"""Extract boundary geometry from a volume/grid as surface mesh."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Extract geometry (boundary surface)")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--extent", type=str, default="",
                        help="Optional crop extent 'xmin,xmax,ymin,ymax,zmin,zmax' "
                             "(empty = full dataset).")
    args = parser.parse_args()

    extent = None
    if args.extent.strip():
        parts = [float(v) for v in args.extent.replace(" ", "").split(",") if v != ""]
        if len(parts) != 6:
            logger.error("--extent must have 6 comma-separated values, got {}", len(parts))
            sys.exit(1)
        extent = parts
        logger.info("Using crop extent: {}", extent)

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells, type={}", ds.n_points, ds.n_cells, type(ds).__name__)

    logger.info("Extracting boundary geometry")
    result = ds.extract_geometry(extent=extent)

    if not isinstance(result, pv.PolyData):
        logger.info("Converting result to PolyData via extract_surface")
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Extracted geometry: {} points, {} cells", result.n_points, result.n_cells)


if __name__ == "__main__":
    main()
