"""Write a pardesline dataset as an nnU-Net v2 raw dataset.

    python prepare_nnunet_dataset.py msd_task09_spleen --out ./nnUNet_raw/Dataset509_Spleen --take 5
    python prepare_nnunet_dataset.py totalsegmentator_ct --image ct --labels liver,spleen,kidney_left,kidney_right --take 3 --out ./Dataset701_Abdomen
    python prepare_nnunet_dataset.py /data/my_study --image ct --mask seg --out ./Dataset900_Mine

Layout written: imagesTr/<case>_0000.nii.gz (one file per channel), labelsTr/<case>.nii.gz,
dataset.json (channel_names, labels, numTraining, file_ending). Images are converted with
SimpleITK (any pardesline volume: NIfTI, MetaImage, NRRD, DICOM series, npz grids). Labels keep
their integer values; several binary mask roles are merged into one label map in the given order
(later roles overwrite earlier ones where they overlap). The split is by sample id; use
pardesline's ``ds.split(by=...)`` for a patient-level split before exporting.

Needs ``pip install "pardesline[medical]"``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", help="bundled name, hf://, tcia://, folder or manifest")
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", help="image role (default: the first volume role)")
    ap.add_argument("--mask", help="label-map role (default: the first labels role)")
    ap.add_argument("--labels", help="comma-separated binary mask roles to merge into one label map")
    ap.add_argument("--take", type=int, help="first N samples only")
    ap.add_argument(
        "--split", default="Tr", help="filter samples whose 'split' field equals this (if present)"
    )
    ap.add_argument("--assume", action="store_true")
    args = ap.parse_args()

    import numpy as np
    import SimpleITK as sitk

    import pardesline as pl

    ds = pl.load(args.dataset, assume=args.assume)
    if args.split and any("split" in s.fields for s in ds._specs):
        ds = ds.filter(split=args.split)
    if args.take:
        ds = ds.take(args.take)
    roles = ds.roles
    image_role = args.image or next(r for r, spec in roles.items() if spec.type == "volume")
    mask_roles = args.labels.split(",") if args.labels else None
    mask_role = args.mask or (
        None if mask_roles else next((r for r, spec in roles.items() if spec.type == "labels"), None)
    )

    out = Path(args.out)
    (out / "imagesTr").mkdir(parents=True, exist_ok=True)
    (out / "labelsTr").mkdir(parents=True, exist_ok=True)
    label_table: dict[str, int] = {"background": 0}
    if mask_roles:
        for i, r in enumerate(mask_roles, start=1):
            label_table[r] = i
    elif mask_role and roles[mask_role].labels:
        for k, name in sorted(roles[mask_role].labels.items()):
            label_table[name] = int(k)

    n = 0
    channels = 1
    for s in ds:
        if image_role not in s.roles:
            continue
        case = re.sub(r"[^A-Za-z0-9]+", "_", s.id).strip("_")
        img = s.get(image_role).to_sitk()
        # multi-channel 4-D NIfTI (MSD brain tumour, prostate) -> one file per channel
        if img.GetDimension() == 4:
            channels = img.GetSize()[3]
            for c in range(channels):
                sitk.WriteImage(img[:, :, :, c], str(out / "imagesTr" / f"{case}_{c:04d}.nii.gz"))
        elif img.GetNumberOfComponentsPerPixel() > 1:
            channels = img.GetNumberOfComponentsPerPixel()
            for c in range(channels):
                sitk.WriteImage(
                    sitk.VectorIndexSelectionCast(img, c), str(out / "imagesTr" / f"{case}_{c:04d}.nii.gz")
                )
        else:
            sitk.WriteImage(img, str(out / "imagesTr" / f"{case}_0000.nii.gz"))
        if mask_roles:
            merged = None
            ref = None
            for i, r in enumerate(mask_roles, start=1):
                if r not in s.roles:
                    continue
                m = s.get(r).to_sitk()
                arr = sitk.GetArrayFromImage(m) > 0
                if merged is None:
                    merged = np.zeros(arr.shape, dtype=np.uint8)
                    ref = m
                merged[arr] = i
            if merged is not None:
                lab = sitk.GetImageFromArray(merged)
                lab.CopyInformation(ref)
                sitk.WriteImage(lab, str(out / "labelsTr" / f"{case}.nii.gz"))
        elif mask_role and mask_role in s.roles:
            lab = s.get(mask_role).to_sitk()
            if lab.GetPixelID() not in (sitk.sitkUInt8, sitk.sitkUInt16):
                lab = sitk.Cast(lab, sitk.sitkUInt8)
            sitk.WriteImage(lab, str(out / "labelsTr" / f"{case}.nii.gz"))
        n += 1
        print(f"  {case}: {img.GetSize()} spacing {tuple(round(x, 3) for x in img.GetSpacing())}")

    dataset_json = {
        "name": ds.name,
        "description": ds.manifest.title or ds.name,
        "reference": ds.manifest.homepage or "",
        "licence": ds.license.describe(),
        "release": "exported by pardesline",
        "channel_names": {
            str(c): (
                "CT"
                if (roles[image_role].modality or "").upper() == "CT"
                else "noNorm"
                if c
                else roles[image_role].modality or "image"
            )
            for c in range(channels)
        },
        "labels": label_table,
        "numTraining": n,
        "file_ending": ".nii.gz",
    }
    (out / "dataset.json").write_text(json.dumps(dataset_json, indent=2), encoding="utf-8")
    print(f"\n{n} case(s) written to {out}; labels {label_table}; licence: {ds.license.describe()}")


if __name__ == "__main__":
    main()
