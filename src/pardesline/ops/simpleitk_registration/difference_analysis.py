"""
Difference Image Analysis for registration quality assessment.

Based on ref_regi/modulesReg.py::display_histogram + display_thresholded_image.
Computes absolute difference between fixed and registered volumes,
highlights regions with high misalignment.

CONTRACT:
    python difference_analysis.py --input <fixed.vti> --output <difference.vti> \
        [--moving <registered.vti>] [--lower_threshold F] [--upper_threshold F]

If --moving is provided, computes |fixed - moving|.
If --moving is omitted, creates a synthetic shifted volume for demo.
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import (
    load_volume, volume_to_vti, compute_difference_thresholded
)
import SimpleITK as sitk
from loguru import logger


def create_synthetic_registered(fixed: sitk.Image) -> sitk.Image:
    """Create a slightly misaligned version for demo (residual error)."""
    transform = sitk.Euler3DTransform()
    center = fixed.TransformContinuousIndexToPhysicalPoint(
        [(sz-1)/2.0 for sz in fixed.GetSize()]
    )
    transform.SetCenter(center)
    transform.SetRotation(0.01, 0.005, -0.008)
    transform.SetTranslation((1.0, -0.5, 0.8))
    logger.info("Synthetic residual: small misalignment for demo")
    return sitk.Resample(fixed, fixed, transform, sitk.sitkLinear, 0.0, fixed.GetPixelID())


def main():
    parser = argparse.ArgumentParser(description="Difference Image Analysis")
    parser.add_argument("--input", required=True, help="Fixed volume (reference)")
    parser.add_argument("--output", required=True, help="Output difference volume")
    parser.add_argument("--moving", default=None, help="Registered/moving volume")
    parser.add_argument("--lower_threshold", type=float, default=50.0)
    parser.add_argument("--upper_threshold", type=float, default=400.0)
    args = parser.parse_args()

    print("PROGRESS:5", flush=True)
    logger.info("Loading fixed: {}", args.input)
    fixed = load_volume(args.input)
    logger.info("Fixed size: {}, spacing: {}", fixed.GetSize(), fixed.GetSpacing())

    print("PROGRESS:20", flush=True)
    if args.moving:
        logger.info("Loading registered/moving: {}", args.moving)
        registered = load_volume(args.moving)
    else:
        logger.info("No --moving provided, creating synthetic misalignment (demo)")
        registered = create_synthetic_registered(fixed)

    print("PROGRESS:40", flush=True)
    logger.info("Computing difference (threshold=[{}, {}])",
                args.lower_threshold, args.upper_threshold)
    diff_image, stats = compute_difference_thresholded(
        fixed, registered,
        lower_threshold=args.lower_threshold,
        upper_threshold=args.upper_threshold,
    )

    print("PROGRESS:80", flush=True)
    logger.info("Saving difference volume: {}", args.output)
    volume_to_vti(diff_image, args.output)

    # Save statistics sidecar
    import json
    out_path = Path(args.output)
    json_path = out_path.with_suffix('.json')
    sidecar = {
        "analysis_type": "difference_image",
        "spacing": list(diff_image.GetSpacing()),
        "origin": list(diff_image.GetOrigin()),
        "direction": list(diff_image.GetDirection()),
        "statistics": stats,
        "parameters": {
            "lower_threshold": args.lower_threshold,
            "upper_threshold": args.upper_threshold,
        },
    }
    json_path.write_text(json.dumps(sidecar, indent=2))
    logger.info("Statistics: {}", json.dumps(stats, indent=2))
    print("PROGRESS:100", flush=True)
    logger.info("Difference analysis completed successfully")


if __name__ == "__main__":
    main()
