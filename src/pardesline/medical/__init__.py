"""Medical volumes with SimpleITK: I/O, DICOM series, registration, segmentation.

Requires the ``[medical]`` extra. The functions are the ones the platform's
registration studio runs; see :mod:`pardesline.medical._service` for the
implementation.
"""

from __future__ import annotations

try:
    import SimpleITK  # noqa: F401
except ImportError:  # pragma: no cover - exercised only without the extra
    from ..errors import MissingDependency

    raise MissingDependency("SimpleITK", "medical") from None

from ._service import (
    add_common_reg_cli_args,
    apply_transform,
    collect_common_reg_opts,
    compute_difference_image,
    compute_difference_thresholded,
    connected_components,
    get_initial_transform,
    load_dicom,
    load_transform,
    load_volume,
    numpy_to_volume,
    register_affine,
    register_bspline,
    register_demons,
    register_rigid,
    register_rigid_advanced,
    resample,
    save_transform,
    save_volume,
    segment_region_growing,
    segment_watershed,
    smooth_gaussian,
    threshold_manual,
    threshold_otsu,
    transform_to_dict,
    volume_metadata,
    volume_to_binary,
    volume_to_vti,
)

__all__ = [
    "add_common_reg_cli_args",
    "apply_transform",
    "collect_common_reg_opts",
    "compute_difference_image",
    "compute_difference_thresholded",
    "connected_components",
    "get_initial_transform",
    "load_dicom",
    "load_transform",
    "load_volume",
    "numpy_to_volume",
    "register_affine",
    "register_bspline",
    "register_demons",
    "register_rigid",
    "register_rigid_advanced",
    "resample",
    "save_transform",
    "save_volume",
    "segment_region_growing",
    "segment_watershed",
    "smooth_gaussian",
    "threshold_manual",
    "threshold_otsu",
    "transform_to_dict",
    "volume_metadata",
    "volume_to_binary",
    "volume_to_vti",
]
