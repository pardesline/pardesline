"""
Otsu automatic thresholding - from 08_segmentation_and_shape_analysis.ipynb.

CONTRACT:
    python otsu_threshold.py --input <volume.vti> --output <segmented.vti>
"""

import argparse
import sys
from pathlib import Path


from pardesline.medical._service import load_volume, volume_to_vti, threshold_otsu
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Otsu Automatic Thresholding")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--number_of_histogram_bins", type=int, default=128, help="Otsu histogram bins")
    parser.add_argument("--inside_value", type=int, default=1, help="Foreground label")
    parser.add_argument("--outside_value", type=int, default=0, help="Background label")
    args = parser.parse_args()

    logger.info("Loading: {}", args.input)
    volume = load_volume(args.input)
    logger.info("Volume size: {}, spacing: {}", volume.GetSize(), volume.GetSpacing())
    logger.info("Pixel type: {}", volume.GetPixelIDTypeAsString())

    logger.info("Computing Otsu threshold")
    binary = threshold_otsu(volume, number_of_histogram_bins=args.number_of_histogram_bins,
                            inside_value=args.inside_value, outside_value=args.outside_value)
    logger.info("Binary result size: {}", binary.GetSize())

    logger.info("Saving: {}", args.output)
    volume_to_vti(binary, args.output)

    logger.info("Otsu thresholding completed successfully")


if __name__ == "__main__":
    main()
