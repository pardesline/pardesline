"""Generate one documentation page per catalog module (algorithm family).

    python docs/_gen/algorithm_pages.py          # writes docs/algorithms/<module>.md and docs/algorithms/index.md

Pages come from the catalog JSON (``src/pardesline/catalog/data/*.json``) and
the defaults rationale (``_defaults.json``): method list, theory text, every
parameter with its type, default, range, description, the reason for the
default and the data the defaults were validated on. Nothing is typed by hand.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _source_date(rel: str) -> str:
    """Date of the last commit touching ``rel`` (repo-relative), today when unknown.

    Keeps the generated pages stable between runs: only a real change to the
    source moves the stamp.
    """
    import datetime as _dt
    import subprocess

    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parents[2],
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        out = ""
    return out or _dt.date.today().isoformat()


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "algorithms"
sys.path.insert(0, str(ROOT / "src"))

# Which high-level call wraps a method, when one exists.
HIGH_LEVEL = {
    "registration.ransac_icp_pipeline": "`target.align(moving)` on a `PointCloud`",
    "registration.icp_refinement": "`points.icp(moving=...)`",
    "registration.ransac_global": "`points.ransac(moving=...)`",
    "simpleitk_registration.rigid": "`fixed.align(moving)` on a `Volume`",
    "point_cloud_reconstruction.poisson": "`points.to_mesh()`",
    "point_cloud_processing.statistical_outlier_removal": "`points.clean()`",
    "point_cloud_processing.voxel_downsample": "`points.downsample(voxel_size=...)`",
    "point_cloud_segmentation.dbscan_clustering": "`points.segment(eps=..., min_points=...)`",
    "mesh_processing.mesh_to_pcd_poisson_disk": "`mesh.to_points(num_points=...)`",
    "mesh_processing.simplification": "`mesh.decimate()`",
    "pyvista_mesh_processing.pv_smooth_taubin": "`mesh.smooth()`",
    "pyvista_mesh_processing.pv_clean": "`mesh.clean()`",
    "simpleitk_segmentation.otsu_threshold": "`volume.segment()`",
    "simpleitk_segmentation.manual_threshold": "`volume.segment(lower=..., upper=...)`",
    "features_extraction.normal_estimation": "`points.normals()`",
}

EXAMPLES = {
    "registration": "[RANSAC + ICP on the Stanford bunny](../examples.md#icp_registration_bunny)",
    "simpleitk_registration": "[SimpleITK rigid registration on RIRE](../examples.md#register_ct_mr_rire)",
    "point_cloud_reconstruction": "[Poisson reconstruction on the Stanford bunny](../examples.md#poisson_reconstruction_bunny)",
    "simpleitk_segmentation": "[Threshold segmentation on MSD spleen](../examples.md#spleen_ct_threshold_segmentation)",
    "lidar_scene_detection": "[Ground removal and clustering on KITTI](../examples.md#kitti_lidar_ground_and_objects)",
    "pyvista_mesh_processing": "[Label map to mesh on MSD hippocampus](../examples.md#hippocampus_mask_to_mesh)",
    "mesh_processing": "[Gaussian splats on the Stanford bunny](../examples.md#points_to_gaussians_bunny)",
    "point_cloud_processing": "[Poisson reconstruction on the Stanford bunny](../examples.md#poisson_reconstruction_bunny)",
}

DATASETS_FOR_EXT = {
    ".ply": [
        "open3d_bunny",
        "open3d_icp_demo",
        "kitti_raw_2011_09_26_drive_0001",
        "medshapenet",
        "c3vd_endoscopy_splats",
    ],
    ".stl": ["medshapenet"],
    ".nii": ["msd_task04_hippocampus", "msd_task09_spleen", "totalsegmentator_ct", "amos22", "ixi_brain_mri"],
    ".mha": ["rire_brain", "liver_tumor_patient01", "visible_human_head_mri", "spider_lumbar_mri"],
    ".vti": [],
    ".pcd": ["open3d_icp_demo"],
    ".png": ["kitti_raw_2011_09_26_drive_0001", "hf_3d_arena"],
    ".obj": ["hf_objaverse_glb_shard"],
}


def _fmt_default(p) -> str:
    v = p.default
    if isinstance(v, bool):
        return "`true`" if v else "`false`"
    if v is None or v == "":
        return '`""`'
    return f"`{v}`"


def _range(p) -> str:
    if p.options:
        return ", ".join(f"`{o}`" for o in p.options)
    if p.min is not None or p.max is not None:
        return f"{p.min} to {p.max}"
    return ""


def page(mod) -> str:
    L: list[str] = []
    title = f"{mod.name} ({mod.id})"
    desc = (mod.description or "").split(". ")[0].strip().rstrip(".")
    L += [
        "---",
        f'title: "{title}: {len(mod.methods)} methods in Python"',
        f'description: "{desc[:150]}"',
        "---",
        "",
    ]
    L += [f"# {mod.name}", "", f"`{mod.id}`: {mod.description}", ""]
    L += ["| | |", "|---|---|"]
    L += [f"| Methods | {', '.join(f'[`{m}`](#{m})' for m in mod.methods)} |"]
    L += [
        f"| Input files | {', '.join(f'`{e}`' for e in mod.input_formats)}{' (and `.nii.gz`)' if '.nii' in mod.input_formats else ''} |"
    ]
    if mod.dual_input:
        L += [
            f"| Two inputs | `input` is the fixed reference, `moving` ({mod.dual_input_label or 'moving'}) is transformed |"
        ]
    ds = []
    for e in mod.input_formats:
        for d in DATASETS_FOR_EXT.get(e, []):
            if d not in ds:
                ds.append(d)
    if ds:
        L += [f"| Bundled datasets to try | {', '.join(f'[`{d}`](../datasets/{d}.md)' for d in ds[:6])} |"]
    if mod.id in EXAMPLES:
        L += [f"| Example | {EXAMPLES[mod.id]} |"]
    L += [f"| CLI | `pardesline run {mod.id}.<method> input.ext [--param value]` |", ""]
    theory = mod.theory or {}
    if theory.get("overview"):
        L += ["## How it works", "", theory["overview"].replace("$$", "\n$$\n"), ""]
    L += ["## Methods", ""]
    for mid, meth in mod.methods.items():
        L += [f"### {mid}", ""]
        mt = (theory.get("methods") or {}).get(mid) or {}
        if mt.get("content"):
            L += [mt["content"], ""]
        hl = HIGH_LEVEL.get(meth.qualname)
        L += ["```python", "import pardesline as pl", ""]
        if meth.dual_input:
            L += [
                'fixed, moving = pl.load("fixed.ply"), pl.load("moving.ply")'
                if ".ply" in mod.input_formats
                else 'fixed, moving = pl.load("fixed.nii.gz"), pl.load("moving.nii.gz")'
            ]
            L += [f'result = fixed.run("{meth.qualname}", moving=moving)  # catalog defaults']
        else:
            ext = mod.input_formats[0] if mod.input_formats else ".ply"
            L += [f'obj = pl.load("input{ext}")', f'result = obj.run("{meth.qualname}")  # catalog defaults']
        if hl:
            L += [f"# same thing, domain vocabulary: {hl}"]
        L += ["result.provenance[-1]  # the step, every parameter used, duration, version", "```", ""]
        L += [
            f"Output: `{meth.output_extension}`. Script: `python -m {meth.python_module} --input ... --output ...`.",
            "",
        ]
        if meth.validated_on:
            L += [f"**Defaults validated on:** {meth.validated_on}", ""]
        if not meth.parameters:
            L += ["No tunable parameters.", ""]
            continue
        L += [
            "| Parameter | Type | Default | Range | What it does | Why this default, when to change it |",
            "|---|---|---|---|---|---|",
        ]
        for p in meth.parameters:
            adv = " *(advanced)*" if p.advanced else ""
            L += [
                f"| `{p.name}`{adv} | {p.type} | {_fmt_default(p)} | {_range(p)} | {p.description.replace('|', '/')} | {p.rationale.replace('|', '/')} |"
            ]
        L += [""]
    L += ["## Related", ""]
    L += [
        "- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)"
    ]
    L += [
        f'- `pl.describe("{mod.id}")` prints this module from the installed package; `pl.describe("{mod.id}.<method>")` one method with ranges and rationale.',
        "",
    ]
    L += [
        f"<sub>Generated from `src/pardesline/catalog/data/{mod.id}.json` and `_defaults.json` on {_source_date(f'src/pardesline/catalog/data/{mod.id}.json')}.</sub>",
        "",
    ]
    return "\n".join(L)


def index(cat) -> str:
    L = [
        "---",
        "title: 3D computer vision and medical imaging algorithms in Python",
        "description: 73 algorithms in 19 families for point clouds, meshes and CT/MRI volumes, each with documented, data-tied defaults: registration (RANSAC, ICP, rigid, affine, B-spline, demons), reconstruction, segmentation, LiDAR, SDF, mesh and volume processing.",
        "---",
        "",
        "# Algorithms",
        "",
        'Nineteen families, 73 methods, 371 parameters, every default documented with the reason it was chosen and the data it was checked on. The methods are Open3D, PyVista/VTK, SimpleITK and SciPy code behind one call; `pl.run("module.method", file, **params)` validates the parameters before anything runs, and the high-level calls (`align`, `segment`, `to_mesh`, `clean`...) pick the method for the object type.',
        "",
        "Start with [Why our defaults work](why-our-defaults-work.md) if you have been burnt by textbook parameters.",
        "",
        "| Family | Methods | Works on | High-level calls |",
        "|---|---|---|---|",
    ]
    for mod in cat:
        hls = [HIGH_LEVEL[m.qualname] for m in mod.methods.values() if m.qualname in HIGH_LEVEL]
        L += [
            f"| [{mod.name}]({mod.id}.md) | {', '.join(f'`{m}`' for m in mod.methods)} | {', '.join(f'`{e}`' for e in mod.input_formats)} | {'; '.join(hls)} |"
        ]
    L += [
        "",
        "## Models",
        "",
        "Deep-learning models (PointNet, DINOv3 features, 3D JEPA, VAE anomaly detection, nnU-Net preparation) are documented under [Models](../models/index.md): reference scripts today, one-line pretrained access on the roadmap.",
        "",
    ]
    return "\n".join(L)


def main() -> None:
    import pardesline as pl

    cat = pl.catalog()
    OUT.mkdir(parents=True, exist_ok=True)
    for mod in cat:
        (OUT / f"{mod.id}.md").write_text(page(mod), encoding="utf-8", newline="\n")
    (OUT / "index.md").write_text(index(cat), encoding="utf-8", newline="\n")
    print(f"wrote {len(cat)} algorithm pages + index to {OUT}")


if __name__ == "__main__":
    main()
