"""Extract the outer surface of a volumetric/unstructured dataset."""
import argparse
import sys
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Extract surface from volume/grid")
    parser.add_argument("--input", required=True, help="Input file (VTK/VTU/VTI)")
    parser.add_argument("--output", required=True, help="Output surface mesh file")
    # Advanced PyVista extract_surface() knobs. pass_pointid / pass_cellid default True
    # (== PyVista defaults). nonlinear_subdivision default 1 (PyVista treats None as 1,
    # so passing 1 is byte-identical to the original no-arg call).
    parser.add_argument("--pass_pointid", type=_b, default=True)
    parser.add_argument("--pass_cellid", type=_b, default=True)
    parser.add_argument("--nonlinear_subdivision", type=int, default=1)
    args = parser.parse_args()

    logger.info("Loading input dataset from {}", args.input)
    ds = pv.read(args.input)
    logger.info("Input dataset type: {}, {} points, {} cells",
                type(ds).__name__, ds.n_points, ds.n_cells)

    logger.info("Extracting outer surface (pass_pointid={}, pass_cellid={}, nonlinear_subdivision={})",
                args.pass_pointid, args.pass_cellid, args.nonlinear_subdivision)
    surface = ds.extract_surface(
        pass_pointid=args.pass_pointid,
        pass_cellid=args.pass_cellid,
        nonlinear_subdivision=args.nonlinear_subdivision,
    )

    logger.info("Saving extracted surface to {}", args.output)
    surface.save(args.output)

    logger.info("Extracted surface: {} points, {} cells",
                surface.n_points, surface.n_cells)


if __name__ == "__main__":
    main()
