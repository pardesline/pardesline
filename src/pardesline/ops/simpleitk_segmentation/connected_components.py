"""
Connected component labeling with size filtering - from 08_segmentation_and_shape_analysis.ipynb.

CONTRACT:
    python connected_components.py --input <volume.vti> --output <labeled.vti> --threshold F --min_size N
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import load_volume, volume_to_vti, threshold_manual, connected_components
import SimpleITK as sitk
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Connected Component Analysis")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--threshold", type=float, default=100.0)
    parser.add_argument("--min_size", type=int, default=15)
    parser.add_argument("--upper_threshold", type=float, default=255.0, help="Upper bound for binarization")
    parser.add_argument("--inside_value", type=int, default=1)
    parser.add_argument("--outside_value", type=int, default=0)
    parser.add_argument("--fully_connected", type=lambda v: str(v).strip().lower() in
                        ("1", "true", "yes", "on", "y", "t"), default=False,
                        help="26-connectivity (True) vs 6-connectivity (False)")
    args = parser.parse_args()

    logger.info("Loading: {}", args.input)
    volume = load_volume(args.input)
    logger.info("Volume size: {}, spacing: {}", volume.GetSize(), volume.GetSpacing())

    logger.info("Binary thresholding at {}", args.threshold)
    binary = sitk.BinaryThreshold(volume, lowerThreshold=args.threshold, upperThreshold=args.upper_threshold,
                                  insideValue=args.inside_value, outsideValue=args.outside_value)

    logger.info("Labeling connected components (min_size={})", args.min_size)
    labeled = connected_components(binary, min_size=args.min_size, fully_connected=args.fully_connected)

    # Convert to float for visualization
    logger.info("Casting labeled image to Float32 for visualization")
    labeled_float = sitk.Cast(labeled, sitk.sitkFloat32)

    logger.info("Saving: {}", args.output)
    volume_to_vti(labeled_float, args.output)

    # Stats
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(labeled)
    num_objects = stats.GetNumberOfLabels()
    logger.info("Found {} objects after size filtering", num_objects)

    logger.info("Connected component analysis completed successfully")


if __name__ == "__main__":
    main()
