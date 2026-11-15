"""
B-spline deformable registration using SimpleITK.

CONTRACT:
    python bspline_registration.py --input <fixed.vti> --output <registered.vti> \
        --moving <moving.vti> [--grid_spacing F] [--num_iterations N]

--moving is required: the moving volume is registered to the fixed one.
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import (registration_quality, check_registration_quality,
                                         DEFAULT_MIN_OVERLAP, DEFAULT_MIN_SIMILARITY)
from pardesline.medical._service import (load_volume, volume_to_vti, register_bspline, transform_to_dict,
                                         DEFAULT_SEED)
import SimpleITK as sitk
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="B-Spline Deformable Registration")
    parser.add_argument("--input", required=True, help="Fixed volume (reference)")
    parser.add_argument("--output", required=True, help="Output registered volume")
    parser.add_argument("--moving", required=True, help="Moving volume to register to fixed")
    parser.add_argument("--grid_spacing", type=float, default=50.0)
    parser.add_argument("--num_iterations", type=int, default=100)
    # Advanced knobs (SDK/API).
    parser.add_argument("--bspline_order", type=int, default=3)
    parser.add_argument("--mesh_coarsening_factor", type=int, default=4,
                        help="Divides the initial mesh; used only with --scale_factors")
    parser.add_argument("--sampling_percentage", type=float, default=0.01)
    parser.add_argument("--interpolator", choices=["LINEAR", "NEAREST", "BSPLINE"], default="LINEAR")
    parser.add_argument("--gradient_convergence_tolerance", type=float, default=1e-5)
    parser.add_argument("--max_number_of_corrections", type=int, default=5)
    parser.add_argument("--cost_function_convergence_factor", type=float, default=1e7)
    parser.add_argument("--bspline_metric", default="mean_squares",
                        choices=["mean_squares", "mattes_mutual_information", "correlation"],
                        help="Metric of the B-spline stage: mean_squares (same modality only) or mutual information")
    parser.add_argument("--scale_factors", type=str, default="",
                        help="Grid refinement per pyramid level, e.g. 1,2,4 (empty: the grid of --grid_spacing)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="Seed of the random metric sampling (positive integer); same seed, same result")
    parser.add_argument("--min_overlap", type=float, default=DEFAULT_MIN_OVERLAP,
                        help="Fail (exit 4) when less than this fraction of the fixed grid maps inside the moving image")
    parser.add_argument("--min_similarity", type=float, default=DEFAULT_MIN_SIMILARITY,
                        help="Fail (exit 4) when the normalised mutual information gain is below this (0 = unrelated)")
    args = parser.parse_args()

    print("PROGRESS:5", flush=True)
    logger.info("Loading fixed: {}", args.input)
    fixed = load_volume(args.input)
    logger.info("Fixed size: {}, spacing: {}", fixed.GetSize(), fixed.GetSpacing())

    print("PROGRESS:15", flush=True)
    logger.info("Loading moving: {}", args.moving)
    moving = load_volume(args.moving)
    logger.info("Moving size: {}, spacing: {}", moving.GetSize(), moving.GetSpacing())

    print("PROGRESS:20", flush=True)
    logger.info("Registering (grid_spacing={} mm, num_iterations={})", args.grid_spacing, args.num_iterations)
    quality: dict = {}
    registered, transform = register_bspline(
        fixed, moving, quality=quality, grid_spacing=args.grid_spacing, num_iterations=args.num_iterations,
        bspline_order=args.bspline_order, mesh_coarsening_factor=args.mesh_coarsening_factor,
        sampling_percentage=args.sampling_percentage, interpolator=args.interpolator,
        gradient_convergence_tolerance=args.gradient_convergence_tolerance,
        max_number_of_corrections=args.max_number_of_corrections,
        cost_function_convergence_factor=args.cost_function_convergence_factor,
        scale_factors=args.scale_factors, seed=args.seed,
        bspline_metric=args.bspline_metric)

    print("PROGRESS:85", flush=True)
    logger.info("Saving registered volume: {}", args.output)
    volume_to_vti(registered, args.output)
    quality.update(registration_quality(fixed, moving, transform))
    check_registration_quality(quality, args.min_overlap, args.min_similarity)
    logger.info("Quality: overlap {}, similarity {}, status {}", quality["overlap"], quality["similarity"],
                quality["status"])

    out_path = Path(args.output)
    import json

    sidecar = {
        "transform_type": "bspline_composite",
        "seed": args.seed,
        "transform": transform_to_dict(transform),
        "quality": quality,
        "spacing": list(registered.GetSpacing()),
        "origin": list(registered.GetOrigin()),
        "direction": list(registered.GetDirection()),
    }
    json_path = out_path.with_suffix('.json')
    json_path.write_text(json.dumps(sidecar, indent=2))
    if quality["status"] != "ok":
        logger.error("Registration quality below the floor: {} (output and {} written for inspection)",
                     "; ".join(quality["failed"]), json_path)
        sys.exit(4)
    logger.info("JSON sidecar saved: {}", json_path)
    print("PROGRESS:100", flush=True)
    logger.info("B-spline registration completed successfully")


if __name__ == "__main__":
    main()
