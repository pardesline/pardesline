"""Extract cells of a specific type from an unstructured grid."""
import argparse
import sys
import pyvista as pv
from pyvista import CellType
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


CELL_TYPE_MAP = {
    "tetrahedral": CellType.TETRA,
    "hexahedral": CellType.HEXAHEDRON,
    "wedge": CellType.WEDGE,
    "pyramid": CellType.PYRAMID,
    "triangle": CellType.TRIANGLE,
    "quad": CellType.QUAD,
}


def main():
    parser = argparse.ArgumentParser(description="Extract cells by type")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cell_type", type=str, default="tetrahedral",
                        help="Cell type: tetrahedral, hexahedral, wedge, pyramid, triangle, quad")
    parser.add_argument("--invert", type=_b, default=False,
                        help="Invert selection (extract all cells NOT of this type).")
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    logger.info("Loaded dataset: {} points, {} cells", ds.n_points, ds.n_cells)
    logger.info("Requested cell type: {}", args.cell_type)

    ct = CELL_TYPE_MAP.get(args.cell_type.lower())
    if ct is None:
        logger.error("Unknown cell type '{}'. Options: {}", args.cell_type, list(CELL_TYPE_MAP.keys()))
        sys.exit(1)

    # Get cell types array and find matching indices
    cell_types = ds.celltypes
    logger.info("Unique cell types in dataset: {}", list(set(cell_types.tolist())))

    mask = cell_types == ct
    indices = mask.nonzero()[0].tolist()

    if not indices:
        logger.warning("No {} cells found. Saving empty dataset.", args.cell_type)
        pv.UnstructuredGrid().save(args.output)
        return

    logger.info("Found {} matching cells out of {} total", len(indices), ds.n_cells)
    logger.info("Extracting cells")
    result = ds.extract_cells(indices, invert=args.invert)
    result.save(args.output)

    logger.info("Extracted {} {} cells from {} total cells", len(indices), args.cell_type, ds.n_cells)


if __name__ == "__main__":
    main()
