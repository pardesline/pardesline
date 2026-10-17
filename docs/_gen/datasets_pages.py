"""Generate one documentation page per bundled dataset from its manifest.

    python docs/_gen/datasets_pages.py           # writes docs/datasets/<name>.md and docs/datasets/index.md

Every fact on a page comes from the manifest (title, description, source,
licence, citation, roles, labels, layouts) or from the catalog (which
algorithms accept each role type). Nothing is typed by hand here; edit the
manifest and regenerate. The MkDocs build runs this through the ``gen-files``
hook in ``docs/_gen/mkdocs_hook.py`` so the pages never go stale.
"""

from __future__ import annotations

import json
import re
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
MANIFESTS = ROOT / "src" / "pardesline" / "data" / "manifests"
OUT = ROOT / "docs" / "datasets"
sys.path.insert(0, str(ROOT / "src"))

TYPE_TO_EXT = {
    "volume": (".nii", ".mha", ".nrrd", ".vti"),
    "labels": (".nii", ".mha", ".nrrd", ".vti"),
    "mesh": (".ply", ".stl", ".obj"),
    "points": (".ply", ".pcd", ".xyz"),
    "splat": (".ply",),
    "image": (".png",),
    "array": (),
    "transform": (),
    "attribute": (),
    "calibration": (),
    "file": (),
}

HIGH_LEVEL = {
    "volume": [
        "`volume.align(moving)`",
        "`volume.segment(lower, upper)`",
        "`volume.to_mesh(isovalue=...)`",
        "`volume.to_sitk()`",
    ],
    "labels": [
        "`mask.to_mesh(label=k)`",
        "`mask.to_numpy()`",
        "metrics: `dice`, `hd95` (evaluation-metrics-3d)",
    ],
    "mesh": [
        "`mesh.to_points(num_points)`",
        "`mesh.decimate()`",
        "`mesh.smooth()`",
        "`mesh.clean()`",
        "`mesh.to_open3d()`",
    ],
    "points": [
        "`points.align(moving)`",
        "`points.clean()`",
        "`points.to_mesh()`",
        "`points.segment(eps, min_points)`",
    ],
    "splat": ["`splat.to_numpy()` (means)", "the `gaussian-splatting` guide"],
    "image": ["`dinov3_features.py` (DINOv2 / DINOv3 patch features)"],
    "array": ["`raw.as_points(...)` / `raw.as_volume(...)` with a layout"],
}


def _module_names_for(ext_list: tuple[str, ...]) -> list[str]:
    import pardesline as pl

    out: list[str] = []
    for mod in pl.catalog():
        if any(mod.accepts(e) for e in ext_list) and mod.id not in out:
            out.append(mod.id)
    return out


def _escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def page(m: dict) -> str:
    name = m["name"]
    src = m["source"]
    lic = m.get("license", {})
    roles = m["roles"]
    lines: list[str] = []
    lines.append("---")
    lines.append(f'title: "{_escape(m.get("title") or name)}"')
    desc = (m.get("description") or "").split(". ")[0].strip().rstrip(".")
    lines.append(f'description: "{_escape(desc)[:155]}"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {m.get('title') or name}")
    lines.append("")
    lines.append(f'`pl.load("{name}")` loads this dataset. {m.get("description", "")}')
    lines.append("")
    lines.append("```python")
    lines.append("import pardesline as pl")
    lines.append("")
    lines.append(f'ds = pl.load("{name}")')
    lines.append("print(ds.describe())  # roles, frames, units, labels, licence, citation")
    first_role = next(iter(roles))
    lines.append("s = ds[0]")
    lines.append(f"obj = s.{first_role}  # fetched now, cached under ~/.cache/pardesline/datasets/{name}")
    lines.append("```")
    lines.append("")
    lines.append("## Provenance and licence")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    scheme = src["scheme"]
    where = {
        "hf": f"Hugging Face Hub repo `{src.get('repo_id')}`"
        + (f", paths `{', '.join(src.get('paths') or [])}`" if src.get("paths") else ""),
        "archive": "remote archive read by HTTP Range: "
        + ", ".join(f"`{u}`" for u in (src.get("urls") or [src.get("url")])),
        "s3": f"public S3 bucket `{src.get('bucket')}`, prefix `{src.get('prefix')}`",
        "tcia": f"The Cancer Imaging Archive, collection `{src.get('collection')}` through the NBIA REST API",
        "urllist": f"URL index `{src.get('index_url')}`",
        "https": "direct HTTPS downloads with checksums: "
        + ", ".join(f"`{k}`" for k in list(src.get("files") or {})[:6]),
        "open3d": "`open3d.data` demo download",
        "local": "local folder",
    }[scheme]
    lines.append(f"| Source | {_escape(where)} |")
    lines.append(f"| Scheme | `{scheme}` |")
    if m.get("size_mb"):
        mb = m["size_mb"]
        lines.append(
            f"| Size of the whole source | {mb / 1024:.1f} GB |"
            if mb >= 1024
            else f"| Size of the whole source | {mb:g} MB |"
        )
    lines.append(
        f"| Licence | {lic.get('spdx') or 'not a standard licence: see the note'}{' (gated: accept the terms at the source first)' if lic.get('requires_agreement') else ''} |"
    )
    if lic.get("commercial") is not None:
        lines.append(
            f"| Commercial use | {'allowed by the licence' if lic.get('commercial') else 'not allowed (non-commercial licence)'} |"
        )
    lines.append(f"| Redistribution | {lic.get('redistribution', 'unknown')} |")
    if lic.get("note"):
        lines.append(f"| Licence note | {_escape(lic['note'])} |")
    if lic.get("source_url"):
        lines.append(f"| Terms | <{lic['source_url']}> |")
    if m.get("homepage"):
        lines.append(f"| Homepage | <{m['homepage']}> |")
    if m.get("citation"):
        lines.append(f"| Cite | {_escape(m['citation'])} |")
    if m.get("pairing"):
        lines.append(f"| Samples grouped by | {m['pairing']} |")
    if m.get("samples"):
        lines.append(f"| Samples listed in the manifest | {len(m['samples'])} |")
    lines.append("")
    lines.append("## Roles (what each sample contains)")
    lines.append("")
    lines.append("| Role | Type | Frame | Units | Labels / layout | Pattern or file |")
    lines.append("|---|---|---|---|---|---|")
    for rname, r in roles.items():
        labels = ""
        if r.get("labels"):
            items = list(r["labels"].items())
            labels = ", ".join(f"{k}={v}" for k, v in items[:8]) + (
                f" … ({len(items)} labels)" if len(items) > 8 else ""
            )
        elif r.get("layout"):
            lay = r["layout"]
            labels = f"layout: {lay.get('dtype', '')} {lay.get('shape', '')} {', '.join(lay.get('columns') or [])}".strip()
        pattern = r.get("pattern") or (
            ", ".join(
                sorted({s["files"][rname] for s in (m.get("samples") or []) if rname in s["files"]})[:3]
            )
            if m.get("samples")
            else ""
        )
        desc_r = r.get("description") or ""
        lines.append(
            f"| `{rname}` | {r['type']}{' (' + r['modality'] + ')' if r.get('modality') else ''} | {r.get('frame') or 'from the file header'} | {r.get('units') or 'from the file header'} | {_escape(labels)} | `{_escape(pattern)}`<br>{_escape(desc_r)} |"
        )
    lines.append("")
    lines.append("## Standardized layout")
    lines.append("")
    lines.append(
        "Files are fetched on first access into the dataset cache and stay in their original format; "
        "`ds.export(folder)` writes every sample as standard files (PLY for points and meshes, MetaImage for volumes and label maps) "
        "with a `.pardesline.json` sidecar carrying frame, units, labels, licence and provenance, plus a manifest for the folder. "
        "Label maps become exact surfaces with `to_mesh(label=k)`, DICOM series become one volume, raw arrays are decoded through the layout above."
    )
    lines.append("")
    lines.append("```python")
    lines.append(f'ds = pl.load("{name}").take(2)')
    lines.append('ds.export("./standardized")        # PLY / MetaImage + sidecars + manifest.json')
    lines.append("```")
    lines.append("")
    lines.append("## Algorithms and models that run on it")
    lines.append("")
    types = sorted({r["type"] for r in roles.values()})
    for t in types:
        calls = HIGH_LEVEL.get(t, [])
        mods = _module_names_for(TYPE_TO_EXT.get(t, ()))
        if not calls and not mods:
            continue
        lines.append(
            f"- **{t}** roles: "
            + ", ".join(calls)
            + (
                " ; catalog modules: " + ", ".join(f"[`{x}`](../algorithms/{x}.md)" for x in mods)
                if mods
                else ""
            )
        )
    if "labels" in types and "volume" in types:
        lines.append(
            "- Supervised segmentation: [`prepare_nnunet_dataset.py`](../models/medical-segmentation.md) writes this dataset in the nnU-Net v2 raw layout; [PointNet](../models/pointnet.md) trains on the label surfaces."
        )
    if "volume" in types:
        lines.append(
            "- Self-supervised pretraining: [3D JEPA](../models/jepa.md) reads the volumes directly."
        )
    if "image" in types:
        lines.append("- Dense features: [DINOv2 / DINOv3](../models/dinov3.md) on the image roles.")
    lines.append("")
    lines.append("## Related")
    lines.append("")
    lines.append(
        "- [Datasets catalog](index.md) · [How to download a medical imaging dataset in Python](../how-to/download-a-medical-imaging-dataset-in-python.md) · [Add a dataset](../contributing.md#adding-a-dataset)"
    )
    tags = ", ".join(f"`{t}`" for t in m.get("tags", []))
    if tags:
        lines.append(f"- Tags: {tags}")
    lines.append("")
    lines.append(
        f"<sub>Generated from `src/pardesline/data/manifests/{name}.json` on {_source_date(f'src/pardesline/data/manifests/{name}.json')}.</sub>"
    )
    lines.append("")
    return "\n".join(lines)


def index(manifests: list[dict]) -> str:
    import io
    from contextlib import redirect_stdout

    import datasets_table
    from datasets_table import main as _unused  # noqa: F401  (same module folder)

    buf = io.StringIO()
    with redirect_stdout(buf):
        datasets_table.main()
    table = buf.getvalue().replace("https://pardesline.github.io/pardesline/datasets/", "")
    table = re.sub(r"\]\(([a-z0-9_]+)/\)", r"](\1.md)", table)
    lines = [
        "---",
        "title: 3D and medical imaging datasets for Python, one line each",
        "description: 43 public 3D and medical imaging datasets (Medical Segmentation Decathlon, TCIA, TotalSegmentator, AMOS, LUNA16, KITTI, Objaverse) loadable in one line with licence, citation and standardized roles.",
        "---",
        "",
        "# Datasets catalog",
        "",
        "Every dataset below loads with one call and comes back as typed objects (volumes, label maps, meshes, point clouds, splats, images) that know their frame, units, labels, licence and citation. Files are fetched on access, verified, cached; archives are read by HTTP Range so one sample costs one sample. `pl.datasets()` lists the names, `pl.describe(name)` prints a manifest.",
        "",
        "```python",
        "import pardesline as pl",
        "",
        "print(pl.datasets())                      # 43 names",
        'print(pl.datasets(tag="ct"))             # by tag',
        'ds = pl.load("msd_task09_spleen")        # lazy: nothing downloaded yet',
        'ct = ds.filter(split="Tr")[0].ct          # one 30 MB volume out of a 1.6 GB tar',
        "```",
        "",
        "Not bundled, and why: BraTS (Synapse data-use agreement), ModelNet, ShapeNet and ScanNet (registration-gated downloads). They are tracked on the [Datasets wanted](https://github.com/pardesline/pardesline/issues?q=is%3Aissue+label%3Adataset) issue; a manifest that fetches with the user's own credentials is welcome.",
        "",
        "## Any source, not only the bundled ones",
        "",
        "| URI | What happens |",
        "|---|---|",
        '| `pl.load("hf://org/repo")` | the Hub tree is listed, a manifest is drafted, you confirm units / labels / licence once, it is saved |',
        '| `pl.load("tcia://Collection")` | a public TCIA collection through the NBIA API, DICOM series as folders |',
        '| `pl.load("s3://openneuro.org/ds000228")` | an OpenNeuro dataset from the public bucket |',
        '| `pl.load("https://.../archive.zip")` | a remote zip or tar read by HTTP Range |',
        '| `pl.scan("/data/study")` | your folder: a draft manifest and the questions the files cannot answer |',
        "",
        "See [How to standardize a folder of medical images](../how-to/standardize-a-folder-of-medical-images-in-python.md) and the [manifest schema](../getting-started/concepts.md#manifest).",
        "",
        "## The bundled manifests",
        "",
        table,
        "",
        '"Size" is the whole source; one sample costs its own size. "See source" means the owner states terms outside a standard licence: `ds.describe()` prints them and the loader warns.',
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(MANIFESTS.glob("*.json"))]
    for m in manifests:
        (OUT / f"{m['name']}.md").write_text(page(m), encoding="utf-8", newline="\n")
    sys.path.insert(0, str(Path(__file__).parent))
    (OUT / "index.md").write_text(index(manifests), encoding="utf-8", newline="\n")
    print(f"wrote {len(manifests)} dataset pages + index to {OUT}")


if __name__ == "__main__":
    main()
