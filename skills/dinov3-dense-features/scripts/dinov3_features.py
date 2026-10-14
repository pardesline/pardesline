"""Extract DINOv3 (or DINOv2) patch features from images, colour them by PCA, save them.

    python dinov3_features.py image.png --out ./feats                  # one image
    python dinov3_features.py ./echo_frames --out ./feats --size 512   # a folder
    python dinov3_features.py scan.png --model facebook/dinov2-large --size 448

Writes <name>.npz (patches (H/p, W/p, d) float16, cls (d,), grid, size) and <name>_pca.png.
Needs torch, transformers, pillow; DINOv3 weights are gated (accept the licence on the Hub,
then `huggingface-cli login`). Grayscale medical images are replicated to three channels.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def load_backbone(name: str):
    import torch
    from transformers import AutoModel

    model = AutoModel.from_pretrained(name)
    model.eval()
    patch = getattr(model.config, "patch_size", 16)
    registers = getattr(model.config, "num_register_tokens", 0)
    return model, patch, registers, torch


def preprocess(path: Path, size: int, patch: int):
    from PIL import Image

    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = size / max(w, h)
    new_w = max(patch, int(round(w * scale / patch)) * patch)
    new_h = max(patch, int(round(h * scale / patch)) * patch)
    img = img.resize((new_w, new_h), Image.BICUBIC)
    arr = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
    return arr.transpose(2, 0, 1)[None], (new_h, new_w)


def pca_rgb(patches: np.ndarray) -> np.ndarray:
    h, w, d = patches.shape
    x = patches.reshape(-1, d).astype(np.float32)
    x = x - x.mean(0)
    u, s, vt = np.linalg.svd(x, full_matrices=False)
    comp = x @ vt[:3].T
    lo, hi = np.percentile(comp, 1, axis=0), np.percentile(comp, 99, axis=0)
    rgb = np.clip((comp - lo) / (hi - lo + 1e-9), 0, 1)
    return (rgb.reshape(h, w, 3) * 255).astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="an image or a folder of images")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="facebook/dinov3-vitl16-pretrain-lvd1689m")
    ap.add_argument("--size", type=int, default=512, help="longest side, rounded to the patch size")
    ap.add_argument("--layer", type=int, default=-1, help="hidden layer to export (-1 = last)")
    args = ap.parse_args()

    model, patch, registers, torch = load_backbone(args.model)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src = Path(args.input)
    files = sorted(
        p
        for p in (src.iterdir() if src.is_dir() else [src])
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
    )
    from PIL import Image

    for f in files:
        x, (h, w) = preprocess(f, args.size, patch)
        with torch.no_grad():
            res = model(pixel_values=torch.from_numpy(x).to(device), output_hidden_states=args.layer != -1)
            hidden = res.last_hidden_state if args.layer == -1 else res.hidden_states[args.layer]
        tokens = hidden[0].float().cpu().numpy()
        cls, patches = tokens[0], tokens[1 + registers :]
        gh, gw = h // patch, w // patch
        patches = patches[: gh * gw].reshape(gh, gw, -1)
        np.savez_compressed(
            out / f"{f.stem}.npz",
            patches=patches.astype(np.float16),
            cls=cls,
            grid=(gh, gw),
            size=(h, w),
            model=args.model,
        )
        Image.fromarray(pca_rgb(patches)).resize((w, h), Image.NEAREST).save(out / f"{f.stem}_pca.png")
        print(f"{f.name}: grid {gh}x{gw}, dim {patches.shape[-1]} -> {out / (f.stem + '.npz')}")


if __name__ == "__main__":
    main()
