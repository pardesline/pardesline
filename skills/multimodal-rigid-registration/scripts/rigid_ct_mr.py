"""Rigid CT / MR registration on the bundled RIRE brain pair, two ways.

1. Through pardesline (one call, parameters from the catalog).
2. Directly with SimpleITK, with every component spelled out and the metric
   traced per iteration, then a checkerboard of fixed vs resampled moving.

    python rigid_ct_mr.py                       # rire_brain
    python rigid_ct_mr.py --fixed ct.nii.gz --moving mr.nii.gz --out ./reg
    python rigid_ct_mr.py --initializer MOMENTS --bins 64 --sampling 0.1

Needs ``pip install "pardesline[medical]"`` (SimpleITK).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def register_sitk(
    fixed, moving, *, initializer: str, bins: int, sampling: float, lr: float, iterations: int, seed: int = 42
):
    import SimpleITK as sitk

    init_mode = sitk.CenteredTransformInitializerFilter.GEOMETRY
    if initializer.upper() == "MOMENTS":
        init_mode = sitk.CenteredTransformInitializerFilter.MOMENTS
    initial = sitk.CenteredTransformInitializer(fixed, moving, sitk.Euler3DTransform(), init_mode)

    reg = sitk.ImageRegistrationMethod()
    reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=bins)
    reg.SetMetricSamplingStrategy(reg.RANDOM)
    reg.SetMetricSamplingPercentage(sampling, seed)
    reg.SetInterpolator(sitk.sitkLinear)
    reg.SetOptimizerAsGradientDescent(
        learningRate=lr, numberOfIterations=iterations, convergenceMinimumValue=1e-6, convergenceWindowSize=10
    )
    reg.SetOptimizerScalesFromPhysicalShift()
    reg.SetShrinkFactorsPerLevel([4, 2, 1])
    reg.SetSmoothingSigmasPerLevel([2, 1, 0])
    reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    reg.SetInitialTransform(initial, inPlace=False)

    trace: list[tuple[int, float]] = []
    levels: list[int] = []
    reg.AddCommand(
        sitk.sitkIterationEvent, lambda: trace.append((reg.GetOptimizerIteration(), reg.GetMetricValue()))
    )
    reg.AddCommand(sitk.sitkMultiResolutionIterationEvent, lambda: levels.append(len(trace)))
    final = reg.Execute(sitk.Cast(fixed, sitk.sitkFloat32), sitk.Cast(moving, sitk.sitkFloat32))
    return final, trace, levels, reg.GetOptimizerStopConditionDescription(), reg.GetMetricValue()


def euler_to_report(t) -> dict:
    import SimpleITK as sitk

    if t.GetName() == "CompositeTransform":  # SimpleITK >= 2 wraps the result when inPlace=False
        t = sitk.CompositeTransform(t).GetNthTransform(0)
    e = sitk.Euler3DTransform(t)
    m = np.array(e.GetMatrix()).reshape(3, 3)
    angle = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(m) - 1) / 2))))
    return {
        "rotation_total_deg": angle,
        "euler_deg": [math.degrees(a) for a in e.GetParameters()[:3]],
        "translation_mm": list(e.GetParameters()[3:6]),
        "center_mm": list(e.GetCenter()),
        "matrix_3x3": m.tolist(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixed")
    ap.add_argument("--moving")
    ap.add_argument("--out", default="./registration_out")
    ap.add_argument("--initializer", default="GEOMETRY", choices=["GEOMETRY", "MOMENTS"])
    ap.add_argument("--bins", type=int, default=50)
    ap.add_argument("--sampling", type=float, default=0.05)
    ap.add_argument("--lr", type=float, default=1.0)
    ap.add_argument("--iterations", type=int, default=200)
    args = ap.parse_args()

    import SimpleITK as sitk

    import pardesline as pl

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.fixed and args.moving:
        fixed_obj, moving_obj = pl.load(args.fixed), pl.load(args.moving)
    else:
        s = pl.load("rire_brain")[0]
        fixed_obj, moving_obj = s.ct, s.mr_t1
    print(
        f"fixed : {fixed_obj.frame.describe()} {fixed_obj.info().get('size')} {fixed_obj.info().get('spacing')}"
    )
    print(
        f"moving: {moving_obj.frame.describe()} {moving_obj.info().get('size')} {moving_obj.info().get('spacing')}"
    )

    # 1. pardesline: one call, catalog-validated parameters
    moved = fixed_obj.align(
        moving_obj,
        metric="mattes_mutual_information",
        number_of_histogram_bins=args.bins,
        initializer=args.initializer,
        sampling_percentage=args.sampling,
        learning_rate=args.lr,
        num_iterations=args.iterations,
    )
    print("\n[pardesline] transform:", json.dumps(moved.transform, default=float)[:600])

    # 2. SimpleITK spelled out
    fixed, moving = fixed_obj.to_sitk(), moving_obj.to_sitk()
    final, trace, levels, stop, metric = register_sitk(
        fixed,
        moving,
        initializer=args.initializer,
        bins=args.bins,
        sampling=args.sampling,
        lr=args.lr,
        iterations=args.iterations,
    )
    report = euler_to_report(final)
    report.update(
        {"final_metric": metric, "stop_condition": stop, "iterations": len(trace), "level_starts": levels}
    )
    print("\n[SimpleITK]", json.dumps(report, indent=2))
    sitk.WriteTransform(final, str(out / "rigid.tfm"))

    resampled = sitk.Resample(moving, fixed, final, sitk.sitkLinear, 0.0, moving.GetPixelID())
    sitk.WriteImage(resampled, str(out / "moving_in_fixed_space.nii.gz"))
    f32 = sitk.Cast(sitk.RescaleIntensity(fixed, 0, 255), sitk.sitkUInt8)
    m32 = sitk.Cast(sitk.RescaleIntensity(resampled, 0, 255), sitk.sitkUInt8)
    checker = sitk.CheckerBoard(f32, m32, [6, 6, 1])
    sitk.WriteImage(checker, str(out / "checkerboard.nii.gz"))
    (out / "metric_trace.json").write_text(json.dumps({"trace": trace, "levels": levels}), encoding="utf-8")

    # did the metric improve within each resolution level? (MI is negated: lower is better)
    bounds = [0, *levels, len(trace)]
    improved = [trace[b][1] >= trace[e - 1][1] for b, e in zip(bounds, bounds[1:], strict=False) if e - 1 > b]
    print(f"\nmetric improved per level: {improved}; outputs in {out}")
    print(
        "Validate with landmarks (TRE) before trusting the pose; the metric value alone is not comparable across pairs."
    )


if __name__ == "__main__":
    main()
