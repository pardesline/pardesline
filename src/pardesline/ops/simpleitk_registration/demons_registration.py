"""
Demons deformable registration using SimpleITK.

CONTRACT:
    python demons_registration.py --input <fixed.vti> --output <registered.vti> \
        --moving <moving.vti> [--num_iterations N] [--standard_deviations F]

--moving is required: the moving volume is registered to the fixed one.
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import (registration_quality, check_registration_quality,
                                         DEFAULT_MIN_OVERLAP, DEFAULT_MIN_SIMILARITY)
from pardesline.medical._service import load_volume, volume_to_vti, register_demons, transform_to_dict
import SimpleITK as sitk
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Demons Deformable Registration")
    parser.add_argument("--input", required=True, help="Fixed volume (reference)")
    parser.add_argument("--output", required=True, help="Output registered volume")
    parser.add_argument("--moving", required=True, help="Moving volume to register to fixed")
    parser.add_argument("--num_iterations", type=int, default=20)
    parser.add_argument("--standard_deviations", type=float, default=2.0)
    parser.add_argument("--smooth_displacement_field", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=True)
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
    logger.info("Registering (num_iterations={}, standard_deviations={})", args.num_iterations, args.standard_deviations)
    quality: dict = {}
    registered, transform = register_demons(fixed, moving, args.num_iterations, args.standard_deviations,
                                            smooth_displacement_field=args.smooth_displacement_field,
                                            quality=quality)

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
        "transform_type": "demons_displacement_field",
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
    logger.info("Demons registration completed successfully")


if __name__ == "__main__":
    main()
