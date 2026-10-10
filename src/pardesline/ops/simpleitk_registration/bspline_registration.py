"""
B-spline deformable registration using SimpleITK.

CONTRACT:
    python bspline_registration.py --input <fixed.vti> --output <registered.vti> \
        [--moving <moving.vti>] [--grid_spacing F] [--num_iterations N]

If --moving is provided, registers moving to fixed (real registration).
If --moving is omitted, creates a synthetic moving for demo purposes.
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import load_volume, volume_to_vti, register_bspline, transform_to_dict
import SimpleITK as sitk
from loguru import logger


def create_synthetic_moving(fixed: sitk.Image) -> sitk.Image:
    """Create synthetic moving with local deformation (demo mode)."""
    transform = sitk.Euler3DTransform()
    center = fixed.TransformContinuousIndexToPhysicalPoint(
        [(sz-1)/2.0 for sz in fixed.GetSize()]
    )
    transform.SetCenter(center)
    transform.SetRotation(0.15, 0.1, -0.1)
    transform.SetTranslation((15.0, -10.0, 12.0))

    logger.info("Synthetic bspline: rotation=(0.15, 0.1, -0.1), translation=(15.0, -10.0, 12.0)")
    moving = sitk.Resample(fixed, fixed, transform, sitk.sitkLinear, 0.0, fixed.GetPixelID())
    return moving


def main():
    parser = argparse.ArgumentParser(description="B-Spline Deformable Registration")
    parser.add_argument("--input", required=True, help="Fixed volume (reference)")
    parser.add_argument("--output", required=True, help="Output registered volume")
    parser.add_argument("--moving", default=None, help="Moving volume to register to fixed")
    parser.add_argument("--grid_spacing", type=float, default=50.0)
    parser.add_argument("--num_iterations", type=int, default=100)
    # Advanced knobs (SDK/API) — defaults reproduce the reference pipeline.
    parser.add_argument("--bspline_order", type=int, default=3)
    parser.add_argument("--mesh_coarsening_factor", type=int, default=4)
    parser.add_argument("--sampling_percentage", type=float, default=0.01)
    parser.add_argument("--interpolator", choices=["LINEAR", "NEAREST", "BSPLINE"], default="LINEAR")
    parser.add_argument("--gradient_convergence_tolerance", type=float, default=1e-5)
    parser.add_argument("--max_number_of_corrections", type=int, default=5)
    parser.add_argument("--cost_function_convergence_factor", type=float, default=1e7)
    parser.add_argument("--scale_factors", type=str, default="1,2,4")
    args = parser.parse_args()

    print("PROGRESS:5", flush=True)
    logger.info("Loading fixed: {}", args.input)
    fixed = load_volume(args.input)
    logger.info("Fixed size: {}, spacing: {}", fixed.GetSize(), fixed.GetSpacing())

    print("PROGRESS:15", flush=True)
    if args.moving:
        logger.info("Loading moving: {}", args.moving)
        moving = load_volume(args.moving)
        logger.info("Moving size: {}, spacing: {}", moving.GetSize(), moving.GetSpacing())
    else:
        logger.info("No --moving provided, creating synthetic moving (demo mode)")
        moving = create_synthetic_moving(fixed)

    print("PROGRESS:20", flush=True)
    logger.info("Registering (grid_spacing={} mm, num_iterations={})", args.grid_spacing, args.num_iterations)
    registered, transform = register_bspline(
        fixed, moving, grid_spacing=args.grid_spacing, num_iterations=args.num_iterations,
        bspline_order=args.bspline_order, mesh_coarsening_factor=args.mesh_coarsening_factor,
        sampling_percentage=args.sampling_percentage, interpolator=args.interpolator,
        gradient_convergence_tolerance=args.gradient_convergence_tolerance,
        max_number_of_corrections=args.max_number_of_corrections,
        cost_function_convergence_factor=args.cost_function_convergence_factor,
        scale_factors=args.scale_factors)

    print("PROGRESS:85", flush=True)
    logger.info("Saving registered volume: {}", args.output)
    volume_to_vti(registered, args.output)

    out_path = Path(args.output)
    import json

    sidecar = {
        "transform_type": "bspline_composite",
        "transform": transform_to_dict(transform),
        "spacing": list(registered.GetSpacing()),
        "origin": list(registered.GetOrigin()),
        "direction": list(registered.GetDirection()),
    }
    json_path = out_path.with_suffix('.json')
    json_path.write_text(json.dumps(sidecar, indent=2))
    logger.info("JSON sidecar saved: {}", json_path)
    print("PROGRESS:100", flush=True)
    logger.info("B-spline registration completed successfully")


if __name__ == "__main__":
    main()
