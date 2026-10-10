"""
Watershed segmentation pipeline - from 08_segmentation_and_shape_analysis.ipynb.

Full pipeline: threshold -> morphological cleanup -> distance map -> seed generation -> watershed -> boundary removal.

CONTRACT:
    python watershed.py --input <volume.vti> --output <segmented.vti> --threshold F --seed_radius F --min_object_size N
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import load_volume, volume_to_vti, segment_watershed
import SimpleITK as sitk
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Watershed Segmentation")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--threshold", type=float, default=100.0)
    parser.add_argument("--seed_radius", type=float, default=10.0)
    parser.add_argument("--min_object_size", type=int, default=15)
    _b = lambda v: str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")  # noqa: E731
    parser.add_argument("--upper_threshold", type=float, default=255.0, help="Upper bound for initial binarization")
    parser.add_argument("--inside_value", type=int, default=1)
    parser.add_argument("--outside_value", type=int, default=0)
    parser.add_argument("--opening_radius", type=str, default="10,10,10", help="BinaryOpening radius per axis")
    parser.add_argument("--closing_radius", type=str, default="10,10,10", help="BinaryClosing radius per axis")
    parser.add_argument("--distance_inside_is_positive", type=_b, default=False)
    parser.add_argument("--distance_squared", type=_b, default=False)
    parser.add_argument("--mark_watershed_line", type=_b, default=True)
    args = parser.parse_args()

    logger.info("Loading: {}", args.input)
    volume = load_volume(args.input)
    logger.info("Volume size: {}, spacing: {}", volume.GetSize(), volume.GetSpacing())

    logger.info("Binary thresholding at {}", args.threshold)
    binary = sitk.BinaryThreshold(volume, lowerThreshold=args.threshold, upperThreshold=args.upper_threshold,
                                  insideValue=args.inside_value, outsideValue=args.outside_value)

    logger.info("Running watershed (seed_radius={}, min_object_size={})", args.seed_radius, args.min_object_size)
    labeled = segment_watershed(binary, seed_radius=args.seed_radius, min_object_size=args.min_object_size,
                                opening_radius=args.opening_radius, closing_radius=args.closing_radius,
                                distance_inside_is_positive=args.distance_inside_is_positive,
                                distance_squared=args.distance_squared,
                                mark_watershed_line=args.mark_watershed_line)

    # Convert to float for visualization
    logger.info("Casting labeled image to Float32 for visualization")
    labeled_float = sitk.Cast(labeled, sitk.sitkFloat32)

    logger.info("Saving: {}", args.output)
    volume_to_vti(labeled_float, args.output)

    # Stats
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(labeled)
    num_objects = stats.GetNumberOfLabels()
    logger.info("Segmented {} objects", num_objects)

    logger.info("Watershed segmentation completed successfully")


if __name__ == "__main__":
    main()
