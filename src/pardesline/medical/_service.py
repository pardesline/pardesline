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

def load_volume(path: str | Path) -> sitk.Image:
    """Load volume from MHA, NRRD, NIFTI, VTI, etc.

    For VTI files: prefers a sibling .mha file if it exists (saved by the
    sample-use endpoint).  Loading .mha via sitk.ReadImage() is ~3x faster
    and uses ~3x less memory than the PyVista→numpy→SimpleITK conversion
    required for VTI.
    """
    path = Path(path)

    # VTI/VTU: check for a native .mha sibling first (much faster loading)
    if path.suffix.lower() in ('.vti', '.vtu'):
        mha_sibling = path.with_suffix('.mha')
        if mha_sibling.exists():
            logger.info(f"Loading native .mha sibling instead of VTI: {mha_sibling}")
            return sitk.ReadImage(str(mha_sibling), sitk.sitkFloat32)

        # Fallback: load via PyVista (slow, 3 memory copies)
        import pyvista as pv
        from .pyvista_adapter import load_pyvista

        logger.warning(f"No .mha sibling for {path.name}; falling back to PyVista loader")
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
        volume = sitk.GetImageFromArray(arr_sitk.astype(np.float32))

        # Set spacing and origin
        volume.SetSpacing(ds.spacing)
        volume.SetOrigin(ds.origin)

        return volume
    else:
        # MHA, NRRD, NIFTI can be loaded directly by SimpleITK
        return sitk.ReadImage(str(path), sitk.sitkFloat32)


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

    return sitk.ReadImage(biggest_files, sitk.sitkFloat32)


def save_volume(volume: sitk.Image, path: str | Path) -> None:
    """Save volume to file."""
    sitk.WriteImage(volume, str(path))


def save_transform(transform: sitk.Transform, path: str | Path) -> None:
    """Save transform to .tfm file."""
    sitk.WriteTransform(transform, str(path))


def transform_to_dict(transform: sitk.Transform) -> dict:
    """Serialize a SimpleITK transform to a JSON-friendly dict."""
    import math
    name = transform.GetName()

    # DisplacementFieldTransform has millions of parameters (one 3D vector per voxel)
    # — serializing them would cause MemoryError. Store summary instead.
    if 'DisplacementField' in name:
        disp_field = transform.GetDisplacementField()
        arr = sitk.GetArrayFromImage(disp_field)
        result = {
            "transform_name": name,
            "field_size": list(disp_field.GetSize()),
            "field_spacing": [round(s, 6) for s in disp_field.GetSpacing()],
            "field_origin": [round(o, 6) for o in disp_field.GetOrigin()],
            "mean_displacement_mm": round(float(arr.mean()), 4),
            "max_displacement_mm": round(float((arr**2).sum(axis=-1).max()**0.5), 4),
            "std_displacement_mm": round(float(arr.std()), 4),
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

    arr = sitk.GetArrayFromImage(volume)
    arr = np.transpose(arr, (2, 1, 0))

    grid = pv.ImageData()
    grid.dimensions = arr.shape
    grid.spacing = volume.GetSpacing()
    grid.origin = volume.GetOrigin()
    grid.point_data["intensity"] = arr.flatten(order="F")

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
                            smoothing_sigmas_in_physical_units=True, optimizer_scales_from_physical_shift=True):
    """Apply the shared metric / gradient-descent optimizer / multi-resolution
    settings. Defaults reproduce the reference pipeline exactly (Mattes MI 50
    bins, RANDOM sampling, linear interp, GD, shrink [4,2,1], sigmas [2,1,0] in
    physical units) so callers that pass nothing are unchanged."""
    if metric == "mean_squares":
        reg.SetMetricAsMeanSquares()
    elif metric == "correlation":
        reg.SetMetricAsCorrelation()
    elif metric == "joint_histogram_mi":
        reg.SetMetricAsJointHistogramMutualInformation()
    else:
        reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=int(number_of_histogram_bins))
    strat = {"NONE": reg.NONE, "REGULAR": reg.REGULAR, "RANDOM": reg.RANDOM}[str(sampling_strategy).upper()]
    reg.SetMetricSamplingStrategy(strat)
    reg.SetMetricSamplingPercentage(float(sampling_percentage))
    reg.SetInterpolator(_SITK_INTERP[str(interpolator).upper()])
    reg.SetOptimizerAsGradientDescent(
        learningRate=float(learning_rate), numberOfIterations=int(num_iterations),
        convergenceMinimumValue=float(convergence_minimum_value),
        convergenceWindowSize=int(convergence_window_size),
    )
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
                    "optimizer_scales_from_physical_shift")


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


def collect_common_reg_opts(args) -> dict:
    """Pull the shared registration knobs from a parsed argparse namespace."""
    return {k: getattr(args, k) for k in _COMMON_REG_ARGS if hasattr(args, k)}


def _find_best_rotation(fixed: sitk.Image, moving: sitk.Image,
                        steps_per_axis: int = 12) -> sitk.Transform:
    """Exhaustive search over rotation space to find best initial alignment.

    Critical for multi-modal (CT/MRI) registration where images may have
    large rotational offsets that gradient descent cannot recover from.
    Searches over all 3 rotation axes in ~15-degree steps.
    """
    import math

    reg = sitk.ImageRegistrationMethod()
    reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    reg.SetMetricSamplingStrategy(reg.RANDOM)
    reg.SetMetricSamplingPercentage(0.05)
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

    best_tx = reg.Execute(fixed, moving)

    params = best_tx.GetParameters()
    logger.info(f"Exhaustive rotation search: rotation=({math.degrees(params[0]):.0f}, "
                f"{math.degrees(params[1]):.0f}, {math.degrees(params[2]):.0f}) deg, "
                f"metric={reg.GetMetricValue():.4f}")

    return best_tx


def register_rigid(fixed: sitk.Image, moving: sitk.Image,
                   learning_rate: float = 1.0, num_iterations: int = 100,
                   sampling_percentage: float = 0.01, initializer: str = "GEOMETRY",
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

    return registered, final_transform


def register_rigid_advanced(fixed: sitk.Image, moving: sitk.Image,
                            learning_rate: float = 0.2, num_iterations: int = 200,
                            sampling_percentage: float = 0.15,
                            exhaustive_steps_per_axis: int = 12,
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

    final_optimized = registration_method.Execute(fixed, moving)

    # Compose transforms
    final_transform = sitk.CompositeTransform([final_optimized, initial_transform])

    logger.info(f"Advanced registration metric: {registration_method.GetMetricValue():.6f}")
    logger.info(f"Stop condition: {registration_method.GetOptimizerStopConditionDescription()}")
    logger.info(f"Total iterations: {len(iteration_data)}")

    registered = sitk.Resample(moving, fixed, final_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
    return registered, final_transform


def register_affine(fixed: sitk.Image, moving: sitk.Image,
                    learning_rate: float = 1.0, num_iterations: int = 100,
                    sampling_percentage: float = 0.01, initializer: str = "GEOMETRY",
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

    return registered, final_transform


def register_bspline(fixed: sitk.Image, moving: sitk.Image, grid_spacing: float = 50.0,
                     num_iterations: int = 100, bspline_order: int = 3,
                     mesh_coarsening_factor: int = 4, sampling_percentage: float = 0.01,
                     interpolator: str = "LINEAR",
                     gradient_convergence_tolerance: float = 1e-5,
                     max_number_of_corrections: int = 5,
                     cost_function_convergence_factor: float = 1e7,
                     scale_factors: str = "1,2,4") -> tuple[sitk.Image, sitk.Transform]:
    """B-spline FFD registration - from 06_advanced_registration.ipynb."""
    # Pre-register with affine
    affine_img, affine_tx = register_affine(fixed, moving)

    # Compute mesh size from grid spacing
    image_size = [s*sp for s,sp in zip(fixed.GetSize(), fixed.GetSpacing())]
    mesh_size = [max(1, int(s/grid_spacing + 0.5)) for s in image_size]
    mesh_size = [max(1, int(m/mesh_coarsening_factor + 0.5)) for m in mesh_size]  # Start coarse

    initial_transform = sitk.BSplineTransformInitializer(fixed, mesh_size, order=int(bspline_order))

    registration_method = sitk.ImageRegistrationMethod()
    registration_method.SetMetricAsMeanSquares()
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(float(sampling_percentage))
    registration_method.SetInterpolator(_SITK_INTERP[str(interpolator).upper()])
    registration_method.SetOptimizerAsLBFGSB(
        gradientConvergenceTolerance=float(gradient_convergence_tolerance),
        numberOfIterations=num_iterations,
        maximumNumberOfCorrections=int(max_number_of_corrections),
        maximumNumberOfFunctionEvaluations=num_iterations * 10,
        costFunctionConvergenceFactor=float(cost_function_convergence_factor)
    )
    registration_method.SetInitialTransformAsBSpline(
        initial_transform, inPlace=True, scaleFactors=_num_list(scale_factors, [1, 2, 4], int))

    final_bspline = registration_method.Execute(fixed, affine_img)

    # Compose affine + bspline
    composite = sitk.CompositeTransform([affine_tx, final_bspline])
    registered = sitk.Resample(moving, fixed, composite, sitk.sitkLinear, 0.0, moving.GetPixelID())

    return registered, composite


def register_demons(fixed: sitk.Image, moving: sitk.Image, num_iterations: int = 20,
                   standard_deviations: float = 2.0,
                   smooth_displacement_field: bool = True) -> tuple[sitk.Image, sitk.Transform]:
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
    return sitk.BinaryThreshold(volume, lowerThreshold=threshold_value,
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
    1. Morphological cleanup
    2. Distance map
    3. Seed generation from distance peaks
    4. Watershed
    5. Boundary object removal
    """
    # Cleanup
    cleaned = sitk.BinaryOpeningByReconstruction(binary_volume, _num_list(opening_radius, [10, 10, 10], int))
    cleaned = sitk.BinaryClosingByReconstruction(cleaned, _num_list(closing_radius, [10, 10, 10], int))

    # Distance map and seeds
    dist = sitk.SignedMaurerDistanceMap(cleaned, insideIsPositive=_sitk_bool(distance_inside_is_positive),
                                        squaredDistance=_sitk_bool(distance_squared))
    seeds = sitk.ConnectedComponent(dist < -seed_radius)
    seeds = sitk.RelabelComponent(seeds, minimumObjectSize=min_object_size)

    # Watershed
    ws = sitk.MorphologicalWatershedFromMarkers(dist, seeds, markWatershedLine=_sitk_bool(mark_watershed_line))
    result = sitk.Mask(ws, sitk.Cast(cleaned, sitk.sitkUInt8))

    # Remove boundary objects
    boundary = sitk.BinaryGrindPeak((ws != 0) | (binary_volume == 0))
    final = sitk.Mask(ws, boundary == 0)

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
            new_size: tuple[int, int, int] | None = None) -> sitk.Image:
    """Resample to new spacing or size."""
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
    resampler.SetInterpolator(sitk.sitkLinear)

    return resampler.Execute(volume)


def smooth_gaussian(volume: sitk.Image, sigma: float = 1.0) -> sitk.Image:
    """Gaussian smoothing."""
    return sitk.SmoothingRecursiveGaussian(volume, sigma=sigma)


def compute_difference_image(fixed: sitk.Image, moving_registered: sitk.Image) -> sitk.Image:
    """Compute difference for registration quality - from modulesReg.py."""
    return sitk.Abs(sitk.Subtract(fixed, moving_registered))


def compute_difference_thresholded(fixed: sitk.Image, registered: sitk.Image,
                                   lower_threshold: float = 50.0,
                                   upper_threshold: float = 400.0) -> tuple[sitk.Image, dict]:
    """Compute difference image and threshold high-intensity regions.

    From ref_regi/modulesReg.py::display_thresholded_image.
    Returns the thresholded binary mask and statistics.
    """
    diff = sitk.Abs(sitk.Subtract(sitk.Cast(fixed, sitk.sitkFloat32),
                                   sitk.Cast(registered, sitk.sitkFloat32)))

    stats = sitk.StatisticsImageFilter()
    stats.Execute(diff)

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
