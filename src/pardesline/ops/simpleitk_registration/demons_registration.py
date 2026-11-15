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
    registered, transform = register_demons(fixed, moving, args.num_iterations, args.standard_deviations,
                                            smooth_displacement_field=args.smooth_displacement_field)

    print("PROGRESS:85", flush=True)
    logger.info("Saving registered volume: {}", args.output)
    volume_to_vti(registered, args.output)

    out_path = Path(args.output)
    import json

    sidecar = {
        "transform_type": "demons_displacement_field",
        "transform": transform_to_dict(transform),
        "spacing": list(registered.GetSpacing()),
        "origin": list(registered.GetOrigin()),
        "direction": list(registered.GetDirection()),
    }
    json_path = out_path.with_suffix('.json')
    json_path.write_text(json.dumps(sidecar, indent=2))
    logger.info("JSON sidecar saved: {}", json_path)
    print("PROGRESS:100", flush=True)
    logger.info("Demons registration completed successfully")


if __name__ == "__main__":
    main()
