"""
SimpleITK core service - wraps ressources_simpleITK utilities.

Reuses code patterns from:
- modulesReg.py
- utilities.py
- notebooks 05_basic_registration.ipynb, 06_advanced_registration.ipynb, 08_segmentation_and_shape_analysis.ipynb
"""

import logging
from pathlib import Path
import numpy as np
import SimpleITK as sitk

logger = logging.getLogger(__name__)


# ============================================================================
# VOLUME I/O
# ============================================================================

def load_volume(path: str | Path, pixel_type=sitk.sitkFloat32) -> sitk.Image:
    """Load volume from MHA, NRRD, NIFTI, VTI, etc.

    VTI files are read through PyVista with their spacing, origin and direction
    matrix. The file named is the file read: a sibling .mha is never substituted
    (it may hold different data or geometry).

    ``pixel_type`` is the type the voxels are cast to (float32 by default, what the
    registration and filtering code expects); ``None`` keeps the stored type, which a
    label map needs: float32 represents integers exactly only up to 2**24.
    """
    path = Path(path)

    if path.suffix.lower() in ('.vti', '.vtu'):
        import pyvista as pv
        from .pyvista_adapter import load_pyvista

        ds = load_pyvista(str(path))
        if not isinstance(ds, pv.ImageData):
            raise ValueError(f"VTI file is not ImageData: {type(ds).__name__}")

        # Convert PyVista ImageData to SimpleITK Image
        arr = ds.point_data.active_scalars
        if arr is None:
            raise ValueError("VTI file has no scalar data")

        # PyVista uses Fortran order (column-major), need to reshape
        dims = ds.dimensions
        arr_3d = arr.reshape(dims, order='F')

        # Convert to SimpleITK (uses C order)
        # Transpose from XYZ (PyVista) to ZYX (SimpleITK)
        arr_sitk = np.transpose(arr_3d, (2, 1, 0))
        volume = sitk.GetImageFromArray(arr_sitk if pixel_type is None else arr_sitk.astype(np.float32))
        if pixel_type is not None and pixel_type != sitk.sitkFloat32:
            volume = sitk.Cast(volume, pixel_type)

        # Geometry: spacing, origin and direction (VTK 9 / PyVista >= 0.45 store a direction)
        volume.SetSpacing(tuple(float(v) for v in ds.spacing))
        volume.SetOrigin(tuple(float(v) for v in ds.origin))
        if hasattr(ds, "direction_matrix"):
            volume.SetDirection(tuple(float(v) for v in np.asarray(ds.direction_matrix).ravel()))

        return volume
    else:
        # MHA, NRRD, NIFTI can be loaded directly by SimpleITK
        if pixel_type is None:
            return sitk.ReadImage(str(path))
        return sitk.ReadImage(str(path), pixel_type)


def load_dicom(folder: str | Path) -> sitk.Image:
    """Load DICOM series from folder.

    Handles folders containing multiple series (e.g. localizers + axial
    stack) by picking the series with the most slices, which is typically
    the main diagnostic volume.  When GDCM detection fails (filenames
    with no extension, broken metadata), groups files by shared image size
    and picks the largest group.
    """
    from pathlib import Path as _Path
    folder_str = str(folder)
    series_IDs = sitk.ImageSeriesReader.GetGDCMSeriesIDs(folder_str)
    print(f"[DICOM] Folder={folder_str} | GDCM found {len(series_IDs)} series", flush=True)

    # Strategy 1: If GDCM found ≥1 series with multiple slices, use the largest.
    # If ReadImage fails (e.g. a "series" contains mixed image sizes, which
    # happens with broken DICOM metadata), fall through to size grouping.
    if series_IDs:
        candidates = []
        for sid in series_IDs:
            files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(folder_str, sid)
            candidates.append((sid, len(files), files))
        candidates.sort(key=lambda x: x[1], reverse=True)
        print(
            f"[DICOM] Series sizes: "
            + ", ".join(f"{sid[:16]}…={n}" for sid, n, _ in candidates[:5]),
            flush=True,
        )

        for chosen_sid, chosen_count, chosen_files in candidates:
            if chosen_count < 2:
                break
            try:
                print(
                    f"[DICOM] Loading GDCM series {chosen_sid[:20]}… ({chosen_count} slices)",
                    flush=True,
                )
                return sitk.ReadImage(chosen_files, sitk.sitkFloat32)
            except Exception as e:
                print(f"[DICOM] Series read failed ({e}); trying next/fallback", flush=True)
                continue

    # Strategy 2: GDCM failed or all series are single-file.
    # Group files by shared 2D image size using sitk.ReadImage() per-file,
    # then pick the largest compatible group and stack them.
    print("[DICOM] GDCM series detection insufficient; grouping files by image size", flush=True)

    all_files = sorted(str(p) for p in _Path(folder).iterdir() if p.is_file())
    if not all_files:
        raise ValueError(f"No files in DICOM folder: {folder}")

    size_groups: dict[tuple, list[str]] = {}
    skipped = 0
    for f in all_files:
        try:
            reader = sitk.ImageFileReader()
            reader.SetFileName(f)
            reader.ReadImageInformation()
            size = tuple(reader.GetSize())
            size_groups.setdefault(size, []).append(f)
        except Exception:
            skipped += 1
            continue

    if not size_groups:
        raise ValueError(
            f"No readable DICOM/medical files in {folder} "
            f"(skipped {skipped} unreadable files)"
        )

    # Pick the largest group (assumed to be the main volume slices)
    biggest_size = max(size_groups.keys(), key=lambda k: len(size_groups[k]))
    biggest_files = size_groups[biggest_size]
    print(
        f"[DICOM] Size groups: "
        + ", ".join(f"{s}={len(fs)}" for s, fs in sorted(size_groups.items(), key=lambda x: -len(x[1]))[:5])
        + f" | chose {biggest_size} with {len(biggest_files)} files",
        flush=True,
    )

    if len(biggest_files) < 2:
        # Truly single-slice — return as-is
        return sitk.ReadImage(biggest_files[0], sitk.sitkFloat32)

    # sitk.ReadImage(list) stacks files in list order: sort them by slice position,
    # Image Position (Patient) projected on the slice normal from Image Orientation.
    keys = [_slice_position(f) for f in biggest_files]
    if all(k is not None for k in keys):
        biggest_files = [f for _, f in sorted(zip(keys, biggest_files))]
    else:
        raise ValueError(
            f"DICOM files in {folder} form no series and lack Image Position / Orientation "
            "(0020,0032 / 0020,0037): slice order and spacing cannot be determined."
        )

    return sitk.ReadImage(biggest_files, sitk.sitkFloat32)


def _slice_position(path: str) -> float | None:
    """Position of a DICOM slice along its normal (mm), or None without the tags."""
    r = sitk.ImageFileReader()
    r.SetFileName(path)
    try:
        r.ReadImageInformation()
    except RuntimeError:
        return None
    if not (r.HasMetaDataKey("0020|0032") and r.HasMetaDataKey("0020|0037")):
        return None
    try:
        o = np.array([float(v) for v in r.GetMetaData("0020|0037").split("\\")])
        p = np.array([float(v) for v in r.GetMetaData("0020|0032").split("\\")])
    except ValueError:
        return None
    if o.size != 6 or p.size != 3:
        return None
    return float(p @ np.cross(o[:3], o[3:]))


def save_volume(volume: sitk.Image, path: str | Path) -> None:
    """Save volume to file."""
    sitk.WriteImage(volume, str(path))


def save_transform(transform: sitk.Transform, path: str | Path) -> None:
    """Save transform to .tfm / .h5 file (composites are flattened first: ITK's
    writers refuse a composite nested in a composite)."""
    if transform.GetName() == "CompositeTransform":
        transform = sitk.CompositeTransform(transform)
        transform.FlattenTransform()
    sitk.WriteTransform(transform, str(path))


def _unwrap(transform: sitk.Transform) -> sitk.Transform:
    """Execute(..., inPlace=False) returns a CompositeTransform holding the result: unwrap it."""
    if transform.GetName() == "CompositeTransform":
        comp = sitk.CompositeTransform(transform)
        if comp.GetNumberOfTransforms() == 1:
            return comp.GetNthTransform(0)
    return transform


def _flat_composite(transforms: list) -> sitk.CompositeTransform:
    """CompositeTransform of ``transforms`` (the LAST one is applied first), flattened so
    that it holds no nested composite and can be written to .h5 / .tfm."""
    comp = sitk.CompositeTransform(list(transforms))
    comp.FlattenTransform()
    return comp


DEFAULT_SEED = 42


def _check_seed(seed) -> int:
    seed = int(seed)
    if seed < 1:
        # SimpleITK reads seed 0 as sitkWallClock: the run would not be reproducible.
        raise ValueError(f"seed must be a positive integer (got {seed}); 0 means 'wall clock' in SimpleITK")
    return seed


def transform_to_dict(transform: sitk.Transform) -> dict:
    """Serialize a SimpleITK transform to a JSON-friendly dict."""
    import math
    name = transform.GetName()

    # DisplacementFieldTransform has millions of parameters (one 3D vector per voxel)
    # — serializing them would cause MemoryError. Store summary instead.
    if 'DisplacementField' in name:
        disp_field = transform.GetDisplacementField()
        # Statistics of the displacement LENGTH per voxel (mm); averaging the signed
        # x, y, z components together would cancel opposite displacements.
        mag = np.linalg.norm(sitk.GetArrayFromImage(disp_field), axis=-1)
        result = {
            "transform_name": name,
            "field_size": list(disp_field.GetSize()),
            "field_spacing": [round(s, 6) for s in disp_field.GetSpacing()],
            "field_origin": [round(o, 6) for o in disp_field.GetOrigin()],
            "mean_displacement_mm": round(float(mag.mean()), 4),
            "max_displacement_mm": round(float(mag.max()), 4),
            "std_displacement_mm": round(float(mag.std()), 4),
        }
        return result

    params = list(transform.GetParameters())
    fixed_params = list(transform.GetFixedParameters())

    result = {
        "transform_name": name,
        "parameters": [round(p, 6) for p in params],
        "fixed_parameters": [round(p, 6) for p in fixed_params],
    }

    # Add human-readable fields for Euler3D
    if 'Euler3D' in name and len(params) >= 6:
        result["rotation_rad"] = [round(params[i], 6) for i in range(3)]
        result["rotation_deg"] = [round(math.degrees(params[i]), 3) for i in range(3)]
        result["translation_mm"] = [round(params[i], 3) for i in range(3, 6)]
        if len(fixed_params) >= 3:
            result["center_mm"] = [round(fixed_params[i], 3) for i in range(3)]

    # Composite transform: serialize each sub-transform
    if 'Composite' in name:
        result["num_transforms"] = transform.GetNumberOfTransforms()
        result["sub_transforms"] = []
        for i in range(transform.GetNumberOfTransforms()):
            sub = transform.GetNthTransform(i)
            result["sub_transforms"].append(transform_to_dict(sub))

    # Affine: add matrix
    if 'Affine' in name and len(params) >= 12:
        result["matrix_3x3"] = [round(params[i], 6) for i in range(9)]
        result["translation_mm"] = [round(params[i], 3) for i in range(9, 12)]

    return result


def load_transform(path: str | Path) -> sitk.Transform:
    """Load transform from .tfm file."""
    return sitk.ReadTransform(str(path))


# ============================================================================
# VOLUME METADATA - Compatible with volume_service.py format
# ============================================================================

def volume_metadata(volume: sitk.Image) -> dict:
    """Extract metadata compatible with volume_service format."""
    size = volume.GetSize()
    spacing = volume.GetSpacing()
    origin = volume.GetOrigin()

    arr = sitk.GetArrayFromImage(volume)

    return {
        "dimensions": [int(size[0]), int(size[1]), int(size[2])],
        "spacing": [float(spacing[0]), float(spacing[1]), float(spacing[2])],
        "origin": [float(origin[0]), float(origin[1]), float(origin[2])],
        "scalar_name": "intensity",
        "scalar_range": [float(arr.min()), float(arr.max())],
    }


def volume_to_binary(volume: sitk.Image) -> bytes:
    """Convert to Float32 binary (Fortran order) - matches volume_service."""
    arr = sitk.GetArrayFromImage(volume)  # ZYX
    arr = np.transpose(arr, (2, 1, 0))  # XYZ
    return arr.astype(np.float32).tobytes()


def numpy_to_volume(array: np.ndarray, reference: sitk.Image | None = None) -> sitk.Image:
    """Convert numpy to SimpleITK volume."""
    volume = sitk.GetImageFromArray(array)
    if reference is not None:
        volume.CopyInformation(reference)
    return volume


def volume_to_vti(volume: sitk.Image, output_path: str | Path) -> None:
    """Convert SimpleITK to VTI for web viewer."""
    import pyvista as pv

    grid = pv.ImageData(dimensions=volume.GetSize(), spacing=volume.GetSpacing(), origin=volume.GetOrigin())
    direction = np.array(volume.GetDirection(), dtype=float).reshape(3, 3)
    if hasattr(grid, "direction_matrix"):
        grid.direction_matrix = direction
    elif not np.allclose(direction, np.eye(3)):
        raise RuntimeError(
            f"PyVista {pv.__version__} cannot store a direction matrix in .vti; this volume is oblique "
            "and would be written axis-aligned. Install pyvista>=0.45 or save as .nrrd / .nii.gz / .mha."
        )
    # C order of the (z, y, x) array = x fastest, the VTK point order
    grid.point_data["intensity"] = sitk.GetArrayFromImage(volume).reshape(-1)

    grid.save(str(output_path))


# ============================================================================
# REGISTRATION - From modulesReg.py and 05_basic_registration.ipynb
# ============================================================================

def get_initial_transform(fixed: sitk.Image, moving: sitk.Image,
                         method: str = "GEOMETRY") -> sitk.Transform:
    """Initialize transform - from modulesReg.py::get_initial_transform.

    GEOMETRY aligns image geometric centers (default, matches ref_regi).
    MOMENTS aligns center of mass + principal axes.
    """
    method = str(method).upper()
    if method not in ("GEOMETRY", "MOMENTS"):
        raise ValueError(f"initializer must be GEOMETRY or MOMENTS, got {method!r}")
    init_method = (sitk.CenteredTransformInitializerFilter.GEOMETRY
                  if method == "GEOMETRY" else
                  sitk.CenteredTransformInitializerFilter.MOMENTS)

    transform = sitk.CenteredTransformInitializer(
        fixed, moving, sitk.Euler3DTransform(), init_method
    )
    logger.info(f"Initial transform ({method}): params={[round(p,3) for p in transform.GetParameters()]}")
    return transform


def _sitk_bool(v) -> bool:
    """Parse a CLI/JSON boolean (values arrive as strings from the runner)."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")


def _num_list(v, default, cast):
    """Parse a comma-separated list like '4,2,1' (or a real list) → [cast(...)]."""
    if v is None:
        return list(default)
    if isinstance(v, (list, tuple)):
        return [cast(x) for x in v]
    return [cast(x) for x in str(v).split(",") if str(x).strip() != ""]


_SITK_INTERP = {
    "LINEAR": sitk.sitkLinear,
    "NEAREST": sitk.sitkNearestNeighbor,
    "BSPLINE": sitk.sitkBSpline,
}


def _configure_registration(reg, *, metric="mattes_mutual_information", number_of_histogram_bins=50,
                            sampling_strategy="RANDOM", sampling_percentage=0.01, interpolator="LINEAR",
                            learning_rate=1.0, num_iterations=100, convergence_minimum_value=1e-6,
                            convergence_window_size=10, shrink_factors="4,2,1", smoothing_sigmas="2,1,0",
                            smoothing_sigmas_in_physical_units=True, optimizer_scales_from_physical_shift=True,
                            seed=DEFAULT_SEED, optimizer="regular_step"):
    """Apply the shared metric / gradient-descent optimizer / multi-resolution
    settings (Mattes MI 50 bins, RANDOM sampling, linear interp, GD, shrink
    [4,2,1], sigmas [2,1,0] in physical units). ``seed`` fixes the random metric
    sampling so that two runs on the same input give the same transform."""
    if metric == "mean_squares":
        reg.SetMetricAsMeanSquares()
    elif metric == "correlation":
        reg.SetMetricAsCorrelation()
    elif metric == "joint_histogram_mi":
        reg.SetMetricAsJointHistogramMutualInformation()
    elif metric == "mattes_mutual_information":
        reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=int(number_of_histogram_bins))
    else:
        raise ValueError(f"unknown metric {metric!r}: mattes_mutual_information, mean_squares, "
                         "correlation or joint_histogram_mi")
    strat = {"NONE": reg.NONE, "REGULAR": reg.REGULAR, "RANDOM": reg.RANDOM}[str(sampling_strategy).upper()]
    reg.SetMetricSamplingStrategy(strat)
    reg.SetMetricSamplingPercentage(float(sampling_percentage), _check_seed(seed))
    reg.SetInterpolator(_SITK_INTERP[str(interpolator).upper()])
    if optimizer == "regular_step":
        reg.SetOptimizerAsRegularStepGradientDescent(
            learningRate=float(learning_rate), minStep=1e-4, numberOfIterations=int(num_iterations),
            relaxationFactor=0.5, gradientMagnitudeTolerance=1e-8,
        )
    elif optimizer == "gradient_descent":
        reg.SetOptimizerAsGradientDescent(
            learningRate=float(learning_rate), numberOfIterations=int(num_iterations),
            convergenceMinimumValue=float(convergence_minimum_value),
            convergenceWindowSize=int(convergence_window_size),
        )
    else:
        raise ValueError(f"optimizer must be regular_step or gradient_descent, got {optimizer!r}")
    if _sitk_bool(optimizer_scales_from_physical_shift):
        reg.SetOptimizerScalesFromPhysicalShift()
    reg.SetShrinkFactorsPerLevel(_num_list(shrink_factors, [4, 2, 1], int))
    reg.SetSmoothingSigmasPerLevel(_num_list(smoothing_sigmas, [2, 1, 0], float))
    if _sitk_bool(smoothing_sigmas_in_physical_units):
        reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    else:
        reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOff()


_COMMON_REG_ARGS = ("metric", "number_of_histogram_bins", "sampling_strategy", "interpolator",
                    "convergence_minimum_value", "convergence_window_size", "shrink_factors",
                    "smoothing_sigmas", "smoothing_sigmas_in_physical_units",
                    "optimizer_scales_from_physical_shift", "seed", "optimizer")


def add_common_reg_cli_args(parser, include_initializer: bool = True) -> None:
    """Register the shared metric/optimizer/multi-resolution CLI flags on a
    registration script's argparse parser (defaults reproduce today's behaviour)."""
    if include_initializer:
        parser.add_argument("--initializer", choices=["GEOMETRY", "MOMENTS"], default="GEOMETRY")
    parser.add_argument("--metric", default="mattes_mutual_information",
                        choices=["mattes_mutual_information", "mean_squares", "correlation", "joint_histogram_mi"])
    parser.add_argument("--number_of_histogram_bins", type=int, default=50)
    parser.add_argument("--sampling_strategy", choices=["NONE", "REGULAR", "RANDOM"], default="RANDOM")
    parser.add_argument("--interpolator", choices=["LINEAR", "NEAREST", "BSPLINE"], default="LINEAR")
    parser.add_argument("--convergence_minimum_value", type=float, default=1e-6)
    parser.add_argument("--convergence_window_size", type=int, default=10)
    parser.add_argument("--shrink_factors", type=str, default="4,2,1")
    parser.add_argument("--smoothing_sigmas", type=str, default="2,1,0")
    parser.add_argument("--smoothing_sigmas_in_physical_units", type=_sitk_bool, default=True)
    parser.add_argument("--optimizer_scales_from_physical_shift", type=_sitk_bool, default=True)
    parser.add_argument("--optimizer", choices=["regular_step", "gradient_descent"], default="regular_step",
                        help="regular_step: step halved on each direction change (converges); gradient_descent: "
                             "fixed learning rate (the pre-0.5 default, stopped early or diverged on simple cases)")
    add_seed_cli_arg(parser)


def add_seed_cli_arg(parser) -> None:
    """``--seed`` of the random metric sampling (a positive integer; 0 would mean wall clock)."""
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="Seed of the random metric sampling (positive integer); same seed, same result")


def collect_common_reg_opts(args) -> dict:
    """Pull the shared registration knobs from a parsed argparse namespace."""
    return {k: getattr(args, k) for k in _COMMON_REG_ARGS if hasattr(args, k)}


def _find_best_rotation(fixed: sitk.Image, moving: sitk.Image,
                        steps_per_axis: int = 12) -> sitk.Transform:
    """Exhaustive search over rotation space to find best initial alignment.

    Critical for multi-modal (CT/MRI) registration where images may have
    large rotational offsets that gradient descent cannot recover from.
    Searches over all 3 rotation axes in ~15-degree steps.

    The metric uses every voxel of the coarse level: at shrink 8 a random 5 %
    sample is a few dozen voxels and made the search pick wrong poses.
    """
    import math

    reg = sitk.ImageRegistrationMethod()
    reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    reg.SetMetricSamplingStrategy(reg.NONE)
    reg.SetInterpolator(sitk.sitkLinear)

    # Search over all 3 rotation axes
    reg.SetOptimizerAsExhaustive(
        numberOfSteps=[steps_per_axis, steps_per_axis, steps_per_axis, 0, 0, 0],
        stepLength=math.pi / steps_per_axis,
    )
    reg.SetOptimizerScales([1.0, 1.0, 1.0, 1e-4, 1e-4, 1e-4])

    init_tx = sitk.CenteredTransformInitializer(
        fixed, moving, sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.MOMENTS,
    )
    reg.SetInitialTransform(init_tx, inPlace=False)

    # Run at very coarse resolution for speed
    reg.SetShrinkFactorsPerLevel([8])
    reg.SetSmoothingSigmasPerLevel([4])
    reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    best_tx = _unwrap(reg.Execute(fixed, moving))

    params = best_tx.GetParameters()
    logger.info(f"Exhaustive rotation search: rotation=({math.degrees(params[0]):.0f}, "
                f"{math.degrees(params[1]):.0f}, {math.degrees(params[2]):.0f}) deg, "
                f"metric={reg.GetMetricValue():.4f}")

    return best_tx


DEFAULT_MIN_OVERLAP = 0.25
DEFAULT_MIN_SIMILARITY = 0.05


class RegistrationQualityError(RuntimeError):
    """A registration whose quality is below the floor the caller set."""


def _fill_quality(quality: dict | None, reg, iterations: int) -> None:
    """The optimiser's own report: final metric value, stop condition, iterations."""
    if quality is None:
        return
    quality.update({
        "final_metric": float(reg.GetMetricValue()),
        "metric_name": "image metric of the registration (lower is better; not comparable across pairs)",
        "stop_condition": reg.GetOptimizerStopConditionDescription(),
        "iterations": int(iterations),
    })


def registration_quality(fixed: sitk.Image, moving: sitk.Image, transform: sitk.Transform,
                         bins: int = 32) -> dict:
    """Quality of a volume registration that does not depend on the method.

    ``overlap``: fraction of the fixed grid whose mapped position falls inside the moving image.
    ``similarity``: normalised mutual information minus 1 on the overlap
    ((H(F) + H(M)) / H(F, M) - 1; 0 for statistically unrelated images, about 0.66-0.77 for an
    exact alignment of the synthetic pairs of tests/test_regressions_core.py, 0.14-0.21 for a
    related but imprecise one, below 0.01 for unrelated content). Valid across modalities.
    """
    reg = sitk.Resample(sitk.Cast(moving, sitk.sitkFloat32), fixed, transform, sitk.sitkLinear,
                        float("nan"), sitk.sitkFloat32)
    a = sitk.GetArrayFromImage(sitk.Cast(fixed, sitk.sitkFloat32)).ravel()
    b = sitk.GetArrayFromImage(reg).ravel()
    inside = np.isfinite(b)
    overlap = float(inside.mean()) if inside.size else 0.0
    similarity = 0.0
    if inside.sum() > 1:
        h, _, _ = np.histogram2d(a[inside], b[inside], bins=int(bins))
        pj = h / h.sum()

        def _entropy(q):
            q = q[q > 0]
            return float(-(q * np.log(q)).sum())

        joint = _entropy(pj.ravel())
        if joint > 0:
            similarity = (_entropy(pj.sum(axis=1)) + _entropy(pj.sum(axis=0))) / joint - 1.0
    return {"overlap": round(overlap, 6), "similarity": round(float(similarity), 6)}


def check_registration_quality(quality: dict, min_overlap: float | None = DEFAULT_MIN_OVERLAP,
                               min_similarity: float | None = DEFAULT_MIN_SIMILARITY) -> dict:
    """Set ``quality["status"]`` (``ok`` / ``below_floor``) and ``quality["floors"]``; return it."""
    floors = {"min_overlap": min_overlap, "min_similarity": min_similarity}
    failed = [f"{k[4:]} {quality.get(k[4:])} < {v}" for k, v in floors.items()
              if v is not None and quality.get(k[4:]) is not None and quality[k[4:]] < v]
    quality["floors"] = floors
    quality["status"] = "below_floor" if failed else "ok"
    if failed:
        quality["failed"] = failed
    return quality


def register_rigid(fixed: sitk.Image, moving: sitk.Image,
                   learning_rate: float = 1.0, num_iterations: int = 300,
                   sampling_percentage: float = 0.1, initializer: str = "GEOMETRY",
                   quality: dict | None = None,
                   **reg_opts) -> tuple[sitk.Image, sitk.Transform]:
    """Rigid registration - exact copy of ref_regi/modulesReg.py::register_images.

    GEOMETRY initialization + Gradient Descent + Multi-resolution [4,2,1].
    Extra optimizer/metric/multi-resolution knobs may be passed via reg_opts
    (see _configure_registration); defaults reproduce the reference pipeline.
    """
    initial_transform = get_initial_transform(fixed, moving, method=initializer)
    registration_method = sitk.ImageRegistrationMethod()
    _configure_registration(registration_method, learning_rate=learning_rate,
                            num_iterations=num_iterations, sampling_percentage=sampling_percentage,
                            **reg_opts)
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    # Iteration logging
    iteration_count = [0]
    def log_iteration():
        iteration_count[0] += 1
        if iteration_count[0] % 10 == 0:
            logger.info(f"  Iteration {iteration_count[0]}: metric = {registration_method.GetMetricValue():.6f}")

    registration_method.AddCommand(sitk.sitkIterationEvent, log_iteration)

    final_transform = registration_method.Execute(fixed, moving)

    import math
    p = final_transform.GetParameters()
    logger.info(f"Final rotation: ({math.degrees(p[0]):.1f}, {math.degrees(p[1]):.1f}, {math.degrees(p[2]):.1f}) deg")
    logger.info(f"Final translation: ({p[3]:.1f}, {p[4]:.1f}, {p[5]:.1f}) mm")
    logger.info(f"Registration metric: {registration_method.GetMetricValue():.6f}")
    logger.info(f"Stop condition: {registration_method.GetOptimizerStopConditionDescription()}")
    logger.info(f"Total iterations: {iteration_count[0]}")

    registered = sitk.Resample(moving, fixed, final_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
    _fill_quality(quality, registration_method, iteration_count[0])

    return registered, final_transform


def register_rigid_advanced(fixed: sitk.Image, moving: sitk.Image,
                            learning_rate: float = 0.2, num_iterations: int = 200,
                            sampling_percentage: float = 0.15,
                            exhaustive_steps_per_axis: int = 12,
                            quality: dict | None = None,
                            **reg_opts) -> tuple[sitk.Image, sitk.Transform]:
    """Advanced rigid registration - from ref_regi/modulesReg.py::registration_advanced.

    Two-stage: exhaustive rotation search + optimized Euler3D, composed together.
    Parameters tuned for better convergence:
    - Lower learning rate (0.2 vs 1.0)
    - More iterations (200 vs 100)
    - Higher sampling (15% vs 1%)
    Phase-2 optimizer/metric/multi-resolution knobs may be passed via reg_opts.
    """
    # Phase 1: Exhaustive rotation search (handles large rotational offsets)
    logger.info("Advanced: Phase 1 - Exhaustive rotation search...")
    initial_transform = _find_best_rotation(fixed, moving, steps_per_axis=int(exhaustive_steps_per_axis))

    registration_method = sitk.ImageRegistrationMethod()
    _configure_registration(registration_method, learning_rate=learning_rate,
                            num_iterations=num_iterations, sampling_percentage=sampling_percentage,
                            **reg_opts)

    # Two-stage: initial + optimized
    optimized_transform = sitk.Euler3DTransform()
    registration_method.SetMovingInitialTransform(initial_transform)
    registration_method.SetInitialTransform(optimized_transform, inPlace=False)

    # Iteration logging
    iteration_data = []
    def log_iteration():
        val = registration_method.GetMetricValue()
        iteration_data.append(val)
        if len(iteration_data) % 10 == 0:
            logger.info(f"  Iteration {len(iteration_data)}: metric = {val:.6f}")

    registration_method.AddCommand(sitk.sitkIterationEvent, log_iteration)

    final_optimized = _unwrap(registration_method.Execute(fixed, moving))

    # Compose: the refinement O was estimated under the moving initial transform M,
    # so the full map is p -> M(O(p)). CompositeTransform applies the LAST listed first.
    final_transform = _flat_composite([initial_transform, final_optimized])

    logger.info(f"Advanced registration metric: {registration_method.GetMetricValue():.6f}")
    logger.info(f"Stop condition: {registration_method.GetOptimizerStopConditionDescription()}")
    logger.info(f"Total iterations: {len(iteration_data)}")

    registered = sitk.Resample(moving, fixed, final_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
    _fill_quality(quality, registration_method, len(iteration_data))
    return registered, final_transform


def register_affine(fixed: sitk.Image, moving: sitk.Image,
                    learning_rate: float = 1.0, num_iterations: int = 300,
                    sampling_percentage: float = 0.1, initializer: str = "GEOMETRY",
                    quality: dict | None = None,
                    **reg_opts) -> tuple[sitk.Image, sitk.Transform]:
    """Affine registration - GEOMETRY initialization like ref_regi."""
    init_filter = (sitk.CenteredTransformInitializerFilter.GEOMETRY
                   if str(initializer).upper() == "GEOMETRY"
                   else sitk.CenteredTransformInitializerFilter.MOMENTS)
    initial_transform = sitk.CenteredTransformInitializer(
        fixed, moving, sitk.AffineTransform(3), init_filter
    )

    registration_method = sitk.ImageRegistrationMethod()
    _configure_registration(registration_method, learning_rate=learning_rate,
                            num_iterations=num_iterations, sampling_percentage=sampling_percentage,
                            **reg_opts)
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    # Iteration logging
    iteration_count = [0]
    def log_iteration():
        iteration_count[0] += 1
        if iteration_count[0] % 10 == 0:
            logger.info(f"  Iteration {iteration_count[0]}: metric = {registration_method.GetMetricValue():.6f}")

    registration_method.AddCommand(sitk.sitkIterationEvent, log_iteration)

    final_transform = registration_method.Execute(fixed, moving)

    logger.info(f"Affine metric: {registration_method.GetMetricValue():.6f}")
    logger.info(f"Stop condition: {registration_method.GetOptimizerStopConditionDescription()}")
    logger.info(f"Total iterations: {iteration_count[0]}")

    registered = sitk.Resample(moving, fixed, final_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
    _fill_quality(quality, registration_method, iteration_count[0])

    return registered, final_transform


def register_bspline(fixed: sitk.Image, moving: sitk.Image, grid_spacing: float = 50.0,
                     num_iterations: int = 100, bspline_order: int = 3,
                     mesh_coarsening_factor: int = 4, sampling_percentage: float = 0.01,
                     interpolator: str = "LINEAR",
                     gradient_convergence_tolerance: float = 1e-5,
                     max_number_of_corrections: int = 5,
                     cost_function_convergence_factor: float = 1e7,
                     scale_factors: str = "",
                     seed: int = DEFAULT_SEED,
                     quality: dict | None = None) -> tuple[sitk.Image, sitk.Transform]:
    """B-spline FFD registration - from 06_advanced_registration.ipynb.

    Affine pre-registration, then a cubic B-spline whose control grid has
    ``grid_spacing`` mm between nodes (mesh size = round(extent / grid_spacing)),
    optimised with LBFGSB over a three-level pyramid (shrink 4, 2, 1; sigmas
    2, 1, 0 mm). With ``scale_factors`` (e.g. "1,2,4") the mesh is first divided
    by ``mesh_coarsening_factor`` and refined at each level instead; that path
    uses the gradient-descent line-search optimiser, since LBFGSB does not
    support a parameter count that changes between levels (SimpleITK 2.5).
    The result maps fixed points to moving points: p -> affine(bspline(p)).
    """
    seed = _check_seed(seed)
    # Pre-register with affine
    affine_img, affine_tx = register_affine(fixed, moving, seed=seed)

    # Compute mesh size from grid spacing
    image_size = [s*sp for s,sp in zip(fixed.GetSize(), fixed.GetSpacing())]
    mesh_size = [max(1, int(s/grid_spacing + 0.5)) for s in image_size]
    refine = _num_list(scale_factors, [], int) if str(scale_factors or "").strip() else []
    if refine:
        mesh_size = [max(1, int(m/mesh_coarsening_factor + 0.5)) for m in mesh_size]  # refined per level

    initial_transform = sitk.BSplineTransformInitializer(fixed, mesh_size, order=int(bspline_order))

    registration_method = sitk.ImageRegistrationMethod()
    registration_method.SetMetricAsMeanSquares()
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(float(sampling_percentage), seed)
    registration_method.SetInterpolator(_SITK_INTERP[str(interpolator).upper()])
    levels = len(refine) if refine else 3
    registration_method.SetShrinkFactorsPerLevel([2 ** k for k in reversed(range(levels))])
    registration_method.SetSmoothingSigmasPerLevel([float(k) for k in reversed(range(levels))])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    if refine:
        registration_method.SetOptimizerAsGradientDescentLineSearch(
            5.0, int(num_iterations), convergenceMinimumValue=1e-4, convergenceWindowSize=5)
        registration_method.SetOptimizerScalesFromPhysicalShift()
        registration_method.SetInitialTransformAsBSpline(initial_transform, inPlace=True, scaleFactors=refine)
    else:
        registration_method.SetOptimizerAsLBFGSB(
            gradientConvergenceTolerance=float(gradient_convergence_tolerance),
            numberOfIterations=num_iterations,
            maximumNumberOfCorrections=int(max_number_of_corrections),
            maximumNumberOfFunctionEvaluations=num_iterations * 10,
            costFunctionConvergenceFactor=float(cost_function_convergence_factor)
        )
        registration_method.SetInitialTransform(initial_transform, inPlace=True)

    final_bspline = _unwrap(registration_method.Execute(fixed, affine_img))

    # Compose: bspline first, then the affine (the LAST listed transform is applied first)
    composite = _flat_composite([affine_tx, final_bspline])
    registered = sitk.Resample(moving, fixed, composite, sitk.sitkLinear, 0.0, moving.GetPixelID())
    _fill_quality(quality, registration_method, registration_method.GetOptimizerIteration())

    return registered, composite


def register_demons(fixed: sitk.Image, moving: sitk.Image, num_iterations: int = 20,
                   standard_deviations: float = 2.0,
                   smooth_displacement_field: bool = True,
                   quality: dict | None = None) -> tuple[sitk.Image, sitk.Transform]:
    """Demons deformable registration - from 06_advanced_registration.ipynb."""
    demons_filter = sitk.FastSymmetricForcesDemonsRegistrationFilter()
    demons_filter.SetNumberOfIterations(num_iterations)
    demons_filter.SetStandardDeviations(standard_deviations)
    demons_filter.SetSmoothDisplacementField(_sitk_bool(smooth_displacement_field))

    # Iteration logging
    iteration_count = [0]
    def log_iteration():
        iteration_count[0] += 1
        metric = demons_filter.GetMetric()
        if iteration_count[0] % 5 == 0:
            logger.info(f"  Demons iteration {iteration_count[0]}: metric = {metric:.6f}")

    demons_filter.AddCommand(sitk.sitkIterationEvent, log_iteration)

    displacement_field = demons_filter.Execute(fixed, moving)
    logger.info(f"Demons completed: {iteration_count[0]} iterations")

    transform = sitk.DisplacementFieldTransform(displacement_field)
    registered = sitk.Resample(moving, fixed, transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
    if quality is not None:
        quality.update({
            "final_metric": float(demons_filter.GetMetric()),
            "metric_name": "demons mean squared difference",
            "stop_condition": f"{demons_filter.GetElapsedIterations()} of {num_iterations} iterations",
            "iterations": int(demons_filter.GetElapsedIterations()),
        })

    return registered, transform


# ============================================================================
# SEGMENTATION - From 08_segmentation_and_shape_analysis.ipynb
# ============================================================================

def threshold_otsu(volume: sitk.Image, number_of_histogram_bins: int = 128,
                   inside_value: int = 1, outside_value: int = 0) -> sitk.Image:
    """Otsu automatic thresholding."""
    otsu = sitk.OtsuThresholdImageFilter()
    otsu.SetNumberOfHistogramBins(int(number_of_histogram_bins))
    otsu.Execute(volume)
    threshold_value = otsu.GetThreshold()
    logger.info(f"Otsu threshold: {threshold_value:.2f}")
    # BinaryThreshold's default upper bound is 255: everything above the threshold is inside.
    upper = max(float(threshold_value), float(sitk.GetArrayViewFromImage(volume).max()))
    return sitk.BinaryThreshold(volume, lowerThreshold=threshold_value, upperThreshold=upper,
                                insideValue=int(inside_value), outsideValue=int(outside_value))


def threshold_manual(volume: sitk.Image, lower: float, upper: float,
                    inside_value: int = 1, outside_value: int = 0) -> sitk.Image:
    """Manual binary threshold."""
    return sitk.BinaryThreshold(volume, lowerThreshold=lower, upperThreshold=upper,
                                insideValue=int(inside_value), outsideValue=int(outside_value))


def segment_region_growing(volume: sitk.Image, seed_points: list[tuple[int, int, int]],
                          lower: float, upper: float) -> sitk.Image:
    """Connected threshold region growing."""
    return sitk.ConnectedThreshold(volume, seedList=seed_points, lower=lower, upper=upper)


def segment_watershed(binary_volume: sitk.Image, seed_radius: float = 10.0,
                     min_object_size: int = 15, opening_radius="10,10,10",
                     closing_radius="10,10,10", distance_inside_is_positive=False,
                     distance_squared=False, mark_watershed_line=True) -> sitk.Image:
    """Watershed segmentation with automatic seed generation - from 08_segmentation_and_shape_analysis.ipynb.

    Steps:
    1. Morphological cleanup (opening / closing radii in voxels)
    2. Signed distance map in mm, negative inside the object
    3. Seeds: regions deeper than ``seed_radius`` mm, at least ``min_object_size`` voxels
    4. Watershed from the seeds, restricted to the object
    5. Objects cut by the image border are removed
    """
    if _sitk_bool(distance_inside_is_positive) or _sitk_bool(distance_squared):
        raise ValueError(
            "distance_inside_is_positive and distance_squared must be false: the seeds are taken "
            "where the distance (mm, negative inside) is below -seed_radius"
        )
    # Cleanup
    cleaned = sitk.BinaryOpeningByReconstruction(binary_volume, _num_list(opening_radius, [10, 10, 10], int))
    cleaned = sitk.BinaryClosingByReconstruction(cleaned, _num_list(closing_radius, [10, 10, 10], int))

    # Distance map (mm: useImageSpacing, whose default is False = voxels) and seeds
    dist = sitk.SignedMaurerDistanceMap(cleaned, insideIsPositive=False, squaredDistance=False,
                                        useImageSpacing=True)
    seeds = sitk.ConnectedComponent(dist < -float(seed_radius))
    seeds = sitk.RelabelComponent(seeds, minimumObjectSize=int(min_object_size))

    # Watershed, labels kept only inside the object (the basins also cover the background)
    ws = sitk.MorphologicalWatershedFromMarkers(dist, seeds, markWatershedLine=_sitk_bool(mark_watershed_line))
    ws = sitk.Mask(ws, sitk.Cast(cleaned, sitk.sitkUInt8))

    a = sitk.GetArrayFromImage(ws)
    # A separate object with no seed of its own was reached through the background by a
    # neighbour's basin and carried its label: such objects are left unlabelled.
    parts = sitk.GetArrayFromImage(sitk.ConnectedComponent(cleaned, True))
    seeded = np.unique(parts[sitk.GetArrayViewFromImage(seeds) > 0])
    a[~np.isin(parts, seeded[seeded != 0])] = 0

    # Remove objects cut by the image border
    border = np.unique(np.concatenate([a[0].ravel(), a[-1].ravel(), a[:, 0].ravel(), a[:, -1].ravel(),
                                       a[:, :, 0].ravel(), a[:, :, -1].ravel()]))
    a[np.isin(a, border[border != 0])] = 0
    final = sitk.GetImageFromArray(a)
    final.CopyInformation(ws)

    return final


def connected_components(binary_volume: sitk.Image, min_size: int = 15,
                        fully_connected: bool = False) -> sitk.Image:
    """Label connected components with size filtering."""
    cc = sitk.ConnectedComponent(binary_volume, _sitk_bool(fully_connected))
    return sitk.RelabelComponent(cc, minimumObjectSize=min_size)


# ============================================================================
# IMAGE PROCESSING
# ============================================================================

def resample(volume: sitk.Image, new_spacing: tuple[float, float, float] | None = None,
            new_size: tuple[int, int, int] | None = None, interpolator: str = "linear") -> sitk.Image:
    """Resample to new spacing or size, same origin and direction, same pixel type.

    ``interpolator``: ``linear`` (default), ``nearest`` (label maps: no new label value is
    invented) or ``bspline``.
    """
    key = str(interpolator).upper()
    if key not in _SITK_INTERP:
        raise ValueError(f"interpolator must be one of {sorted(k.lower() for k in _SITK_INTERP)}, got {interpolator!r}")
    original_spacing = volume.GetSpacing()
    original_size = volume.GetSize()

    if new_spacing is None and new_size is None:
        new_spacing = (1.0, 1.0, 1.0)

    if new_spacing is not None:
        new_size = tuple(int(round(osz * ospc / nspc))
                        for osz, ospc, nspc in zip(original_size, original_spacing, new_spacing))
    else:
        new_spacing = tuple(ospc * osz / nsz
                           for ospc, osz, nsz in zip(original_spacing, original_size, new_size))

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing(new_spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(volume.GetDirection())
    resampler.SetOutputOrigin(volume.GetOrigin())
    resampler.SetTransform(sitk.Transform())
    resampler.SetDefaultPixelValue(0)
    resampler.SetInterpolator(_SITK_INTERP[key])

    return resampler.Execute(volume)


def smooth_gaussian(volume: sitk.Image, sigma: float = 1.0) -> sitk.Image:
    """Gaussian smoothing."""
    return sitk.SmoothingRecursiveGaussian(volume, sigma=sigma)


def compute_difference_image(fixed: sitk.Image, moving_registered: sitk.Image) -> sitk.Image:
    """Compute difference for registration quality - from modulesReg.py."""
    return sitk.Abs(sitk.Subtract(fixed, moving_registered))


def compute_difference_thresholded(fixed: sitk.Image, registered: sitk.Image,
                                   lower_threshold: float = 50.0,
                                   upper_threshold: float | None = None) -> tuple[sitk.Image, dict]:
    """Compute difference image and threshold high-intensity regions.

    From ref_regi/modulesReg.py::display_thresholded_image.
    Returns the difference image and statistics; ``high_diff_voxels`` counts the
    voxels with lower_threshold <= |fixed - registered| <= upper_threshold (no
    upper bound by default: a larger difference is a worse alignment, never a better one).
    """
    diff = sitk.Abs(sitk.Subtract(sitk.Cast(fixed, sitk.sitkFloat32),
                                   sitk.Cast(registered, sitk.sitkFloat32)))

    stats = sitk.StatisticsImageFilter()
    stats.Execute(diff)
    if upper_threshold is None:
        upper_threshold = max(float(lower_threshold), float(stats.GetMaximum()))

    diff_arr = sitk.GetArrayFromImage(diff)
    total_voxels = diff_arr.size
    nonzero_voxels = int(np.count_nonzero(diff_arr))

    thresholded = sitk.BinaryThreshold(diff,
                                        lowerThreshold=lower_threshold,
                                        upperThreshold=upper_threshold,
                                        insideValue=1, outsideValue=0)

    thresh_arr = sitk.GetArrayFromImage(thresholded)
    high_diff_voxels = int(np.count_nonzero(thresh_arr))

    statistics = {
        "mean_difference": float(stats.GetMean()),
        "max_difference": float(stats.GetMaximum()),
        "std_difference": float(stats.GetSigma()),
        "total_voxels": total_voxels,
        "high_diff_voxels": high_diff_voxels,
        "high_diff_percentage": round(100.0 * high_diff_voxels / total_voxels, 3),
    }

    logger.info(f"Difference stats: mean={statistics['mean_difference']:.2f}, "
                f"max={statistics['max_difference']:.2f}, "
                f"high_diff={statistics['high_diff_percentage']:.1f}%")

    # Return the difference image (not the binary mask) for visualization
    return diff, statistics


def apply_transform(volume: sitk.Image, transform: sitk.Transform,
                   reference: sitk.Image | None = None) -> sitk.Image:
    """Apply transform to volume."""
    if reference is None:
        reference = volume
    return sitk.Resample(volume, reference, transform, sitk.sitkLinear, 0.0, volume.GetPixelID())
