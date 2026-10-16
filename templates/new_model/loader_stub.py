"""Loader stub for a model manifest: what the registry will do for this model.

    python templates/new_model/loader_stub.py manifest.json --dry-run

Today it validates the manifest and prints the plan (download, instantiate,
preprocess, run, postprocess). When the model registry lands, the same four
functions become the model's entry points; keep them pure (no global state).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = ("name", "task", "input", "output", "source", "runtime", "license", "provenance")


def validate(manifest: dict) -> list[str]:
    problems = [f"missing field: {k}" for k in REQUIRED if k not in manifest]
    lic = manifest.get("license", {})
    if not (lic.get("spdx") or lic.get("note")):
        problems.append("license: spdx or note required")
    if manifest.get("input", {}).get("type") not in ("volume", "labels", "points", "mesh", "image", "splat"):
        problems.append("input.type must be a pardesline object type")
    if "weights" in json.dumps(manifest).lower() and manifest.get("source", {}).get("scheme") == "local":
        problems.append("weights must not be shipped in the repository")
    return problems


def download(manifest: dict, cache: Path) -> Path:
    """Fetch the weight files into the cache (Hub, HTTPS with checksum, torch.hub). Not implemented yet."""
    raise NotImplementedError("the model registry runner will implement downloads")


def preprocess(manifest: dict, obj):
    """Resample / window / normalise a pardesline object to what the model expects."""
    raise NotImplementedError


def predict(model, batch):
    """Run the model."""
    raise NotImplementedError


def postprocess(manifest: dict, raw, like):
    """Turn the raw output into a pardesline object (LabelMap with the manifest's labels, feature array...)."""
    raise NotImplementedError


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--dry-run", action="store_true", help="validate and print the plan")
    args = ap.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    problems = validate(manifest)
    if problems:
        raise SystemExit("\n".join(problems))
    src, rt = manifest["source"], manifest["runtime"]
    print(
        f"{manifest['name']}: {manifest['task']} on {manifest['input']['type']} -> {manifest['output']['type']}"
    )
    print(f"1. download from {src.get('scheme')} {src.get('repo_id') or src.get('url') or src.get('repo')}")
    print(
        f"2. instantiate with {rt['framework']} {rt.get('framework_version', '')} (+ {', '.join(rt.get('extra_packages', []))})"
    )
    print(f"3. preprocess to {manifest['input'].get('spacing_mm')} mm, {manifest['input'].get('intensity')}")
    print("4. predict, then postprocess into a pardesline object with the manifest's labels")
    print(
        f"licence: {manifest['license'].get('spdx') or 'see note'}; needs agreement: {manifest['license'].get('requires_agreement', False)}"
    )


if __name__ == "__main__":
    main()
