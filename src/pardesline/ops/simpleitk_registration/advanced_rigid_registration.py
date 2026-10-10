"""
Advanced rigid registration using SimpleITK (two-stage composite transform).

Based on ref_regi/modulesReg.py::registration_advanced:
- Lower learning rate (0.2) for stability
- Higher sampling (15%) for accuracy
- More iterations (200) for convergence
- Two-stage: initial geometry alignment + optimized Euler3D, composed together

CONTRACT:
    python advanced_rigid_registration.py --input <fixed.vti> --output <registered.vti> \
        [--moving <moving.vti>] [--learning_rate F] [--num_iterations N] [--sampling_percentage F]
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import (load_volume, volume_to_vti, register_rigid_advanced,
                                         transform_to_dict, add_common_reg_cli_args, collect_common_reg_opts)
import SimpleITK as sitk
from loguru import logger


def create_synthetic_moving(fixed: sitk.Image) -> sitk.Image:
    """Create synthetic moving image by applying known transform (demo mode)."""
    transform = sitk.Euler3DTransform()
    center = fixed.TransformContinuousIndexToPhysicalPoint(
        [(sz-1)/2.0 for sz in fixed.GetSize()]
    )
    transform.SetCenter(center)
    transform.SetRotation(0.1, 0.05, -0.08)
    transform.SetTranslation((10.0, -5.0, 8.0))
    logger.info("Synthetic transform: rotation=(0.1, 0.05, -0.08) rad, translation=(10.0, -5.0, 8.0) mm")
    moving = sitk.Resample(fixed, fixed, transform, sitk.sitkLinear, 0.0, fixed.GetPixelID())
    return moving


def main():
    parser = argparse.ArgumentParser(description="Advanced Rigid Registration")
    parser.add_argument("--input", required=True, help="Fixed volume (reference)")
    parser.add_argument("--output", required=True, help="Output registered volume")
    parser.add_argument("--moving", default=None, help="Moving volume to register")
    parser.add_argument("--learning_rate", type=float, default=0.2)
    parser.add_argument("--num_iterations", type=int, default=200)
    parser.add_argument("--sampling_percentage", type=float, default=0.15)
    parser.add_argument("--exhaustive_steps_per_axis", type=int, default=12)
    add_common_reg_cli_args(parser, include_initializer=False)
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
    logger.info("Advanced rigid registration (lr={}, iter={}, sampling={}%)",
                args.learning_rate, args.num_iterations, args.sampling_percentage * 100)
    registered, transform = register_rigid_advanced(
        fixed, moving,
        learning_rate=args.learning_rate,
        num_iterations=args.num_iterations,
        sampling_percentage=args.sampling_percentage,
        exhaustive_steps_per_axis=args.exhaustive_steps_per_axis,
        **collect_common_reg_opts(args),
    )

    print("PROGRESS:85", flush=True)
    logger.info("Saving registered volume: {}", args.output)
    volume_to_vti(registered, args.output)

    import json
    out_path = Path(args.output)
    sidecar = {
        "transform_type": "advanced_rigid",
        "transform": transform_to_dict(transform),
        "spacing": list(registered.GetSpacing()),
        "origin": list(registered.GetOrigin()),
        "direction": list(registered.GetDirection()),
        "parameters": {
            "learning_rate": args.learning_rate,
            "num_iterations": args.num_iterations,
            "sampling_percentage": args.sampling_percentage,
        },
    }
    json_path = out_path.with_suffix('.json')
    json_path.write_text(json.dumps(sidecar, indent=2))
    logger.info("JSON sidecar saved: {}", json_path)
    print("PROGRESS:100", flush=True)
    logger.info("Advanced rigid registration completed successfully")


if __name__ == "__main__":
    main()
