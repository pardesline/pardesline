"""Randomly sample a fraction of points from a dataset."""
import argparse
import sys
import numpy as np
import pyvista as pv
from loguru import logger


def _b(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def main():
    parser = argparse.ArgumentParser(description="Random point sampling")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fraction", type=float, default=0.5, help="Fraction of points to keep")
    # Advanced knobs. replace defaults to False (original hardcoded np.random.choice replace=False);
    # seed=-1 sentinel means no seeding (original behavior, uses global RNG state);
    # adjacent_cells / include_cells passed to extract_points (PyVista defaults True).
    parser.add_argument("--replace", type=_b, default=False)
    parser.add_argument("--seed", type=int, default=0, help="Random seed (same seed, same points)")
    parser.add_argument("--adjacent_cells", type=_b, default=True)
    parser.add_argument("--include_cells", type=_b, default=True)
    args = parser.parse_args()

    logger.info("Loading input: {}", args.input)
    ds = pv.read(args.input)
    if not isinstance(ds, pv.PolyData):
        logger.info("Converting to PolyData via extract_surface")
        ds = ds.extract_surface()

    n = ds.n_points
    logger.info("Loaded dataset: {} points", n)
    logger.info("Sampling fraction: {:.1f}%", args.fraction * 100)
    logger.info("Advanced: replace={}, seed={}, adjacent_cells={}, include_cells={}",
                args.replace, args.seed, args.adjacent_cells, args.include_cells)

    if n == 0:
        logger.error("Input has no points")
        sys.exit(1)

    rng = np.random.default_rng(args.seed if args.seed >= 0 else None)
    if args.seed < 0:
        logger.warning("seed {} < 0: unseeded, the selection changes from run to run", args.seed)

    n_keep = max(1, int(n * args.fraction))
    logger.info("Selecting {} points from {} total", n_keep, n)
    indices = np.sort(rng.choice(n, size=n_keep, replace=args.replace))

    if args.replace:
        # extract_points collapses repeated indices: write the duplicates explicitly.
        result = pv.PolyData(np.asarray(ds.points)[indices])
        for name in ds.point_data.keys():
            result.point_data[name] = np.asarray(ds.point_data[name])[indices]
        result.save(args.output)
        logger.info("Random sample with replacement: {} -> {} points ({} distinct)", n, result.n_points,
                    len(np.unique(indices)))
        return

    logger.info("Extracting sampled points")
    result = ds.extract_points(indices, adjacent_cells=args.adjacent_cells, include_cells=args.include_cells)
    if not isinstance(result, pv.PolyData):
        result = result.extract_surface()

    result.save(args.output)
    logger.info("Random sample ({:.0f}%): {} -> {} points", args.fraction * 100, n, result.n_points)


if __name__ == "__main__":
    main()
