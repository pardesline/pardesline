"""
Rigid registration using SimpleITK.

CONTRACT:
    python rigid_registration.py --input <fixed.vti> --output <registered.vti> \
        --moving <moving.vti> [--learning_rate F] [--num_iterations N]

--moving is required: the moving volume is registered to the fixed one.
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import (registration_quality, check_registration_quality,
                                         DEFAULT_MIN_OVERLAP, DEFAULT_MIN_SIMILARITY)
from pardesline.medical._service import (load_volume, volume_to_vti, register_rigid, transform_to_dict,
                                         add_common_reg_cli_args, collect_common_reg_opts)
import SimpleITK as sitk
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Rigid Registration")
    parser.add_argument("--input", required=True, help="Fixed volume (reference)")
    parser.add_argument("--output", required=True, help="Output registered volume")
    parser.add_argument("--moving", required=True, help="Moving volume to register to fixed")
    parser.add_argument("--learning_rate", type=float, default=1.0)
    parser.add_argument("--num_iterations", type=int, default=300)
    parser.add_argument("--sampling_percentage", type=float, default=0.1)
    add_common_reg_cli_args(parser)
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
    logger.info("Registering (lr={}, iter={}, sampling={}%)",
                args.learning_rate, args.num_iterations, args.sampling_percentage * 100)
    quality: dict = {}
    registered, transform = register_rigid(fixed, moving, quality=quality,
                                           learning_rate=args.learning_rate,
                                           num_iterations=args.num_iterations,
                                           sampling_percentage=args.sampling_percentage,
                                           initializer=args.initializer,
                                           **collect_common_reg_opts(args))

    print("PROGRESS:85", flush=True)
    logger.info("Saving registered volume: {}", args.output)
    volume_to_vti(registered, args.output)
    quality.update(registration_quality(fixed, moving, transform))
    check_registration_quality(quality, args.min_overlap, args.min_similarity)
    logger.info("Quality: overlap {}, similarity {}, status {}", quality["overlap"], quality["similarity"],
                quality["status"])

    import json
    out_path = Path(args.output)
    sidecar = {
        "transform_type": "rigid",
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
    logger.info("Transform JSON saved: {}", json_path)
    print("PROGRESS:100", flush=True)
    logger.info("Rigid registration completed successfully")


if __name__ == "__main__":
    main()
