---
title: How-to guides — 3D vision and medical imaging tasks in Python
description: One page per task, titled as the question practitioners ask: download and standardize datasets, DICOM to NIfTI, raw point clouds, ICP and RANSAC that converge, CT/MR registration, masks to meshes, CT segmentation, surface reconstruction, atlas labelling, Gaussian splats, pretrained segmentation models, DINOv3 features.
---

# How-to guides

Each page answers one question with runnable code on a bundled dataset, the expected output, and what to do when it fails. The code ran on 2026-10-16 with `pip install "pardesline[all]"`.

## Datasets

- [How to download a medical imaging dataset in Python](download-a-medical-imaging-dataset-in-python.md)
- [How to load a Hugging Face 3D dataset in Python](load-a-hugging-face-3d-dataset-in-python.md)
- [How to download a TCIA collection in Python](download-a-tcia-collection-in-python.md)
- [How to standardize a folder of medical images in Python](standardize-a-folder-of-medical-images-in-python.md)
- [How to convert a DICOM series to NIfTI in Python](convert-a-dicom-series-to-nifti-in-python.md)
- [How to load raw .npy and .bin point clouds with a layout](load-raw-npy-and-bin-point-clouds-with-a-layout.md)

## Algorithms

- [How to register two point clouds with ICP in Python](register-two-point-clouds-with-icp-in-python.md)
- [How to fix ICP that does not converge](fix-icp-that-does-not-converge.md)
- [How to fix RANSAC global registration that fails](fix-ransac-global-registration-that-fails.md)
- [How to register CT and MRI of the same patient in Python](register-ct-and-mri-of-the-same-patient-in-python.md)
- [How to turn a segmentation mask into a mesh in Python](turn-a-segmentation-mask-into-a-mesh-in-python.md)
- [How to segment organs in a CT scan in Python](segment-organs-in-a-ct-scan-in-python.md)
- [How to reconstruct a surface from a point cloud in Python](reconstruct-a-surface-from-a-point-cloud-in-python.md)
- [How to align two scans in Python](align-two-scans-in-python.md)
- [How to label a scan from an atlas in Python](label-a-scan-from-an-atlas-in-python.md)
- [How to convert a point cloud to Gaussian splats in Python](convert-a-point-cloud-to-gaussian-splats-in-python.md)

## Models

- [How to run a pretrained 3D segmentation model on your CT scans](run-a-pretrained-3d-segmentation-model-on-your-ct-scans.md)
- [How to extract DINOv3 features from medical images in Python](extract-dinov3-features-from-medical-images-in-python.md)
