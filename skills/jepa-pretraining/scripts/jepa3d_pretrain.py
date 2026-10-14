"""3D JEPA pretraining on medical volumes (reference implementation).

Context encoder (3D ViT) -> predictor (narrow ViT with mask tokens at target positions)
-> L2 against the EMA target encoder's embeddings of the masked blocks. No decoder.

    python jepa3d_pretrain.py --dataset totalsegmentator_ct --role ct --take 200 --crop 96 --epochs 100 --out ./runs/jepa
    python jepa3d_pretrain.py --dataset ixi_brain_mri --role t1 --modality mr --crop 64 --patch 8 --dim 192 --epochs 20
    python jepa3d_pretrain.py --smoke          # synthetic volumes, CPU, seconds

Volumes come from any pardesline dataset (lazy download), are resampled to an isotropic
spacing, intensity-windowed per modality (CT: clip -1000..1000 HU; MR: per-volume z-score),
and cropped at random to crop^3. Needs torch and pardesline[medical].
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import time
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError as exc:  # pragma: no cover
    raise SystemExit("this script needs PyTorch: pip install torch") from exc


# ---------------------------------------------------------------------------- model
class PatchEmbed3D(nn.Module):
    def __init__(self, patch: int, dim: int, in_ch: int = 1):
        super().__init__()
        self.proj = nn.Conv3d(in_ch, dim, kernel_size=patch, stride=patch)

    def forward(self, x):  # (B, 1, D, H, W) -> (B, N, dim)
        return self.proj(x).flatten(2).transpose(1, 2)


def sincos_3d(grid: tuple[int, int, int], dim: int) -> torch.Tensor:
    """Fixed 3-D sine-cosine position embedding, (N, dim)."""
    assert dim % 6 == 0, "dim must be divisible by 6 for 3-D sincos"
    d = dim // 3
    out = []
    for axis, n in enumerate(grid):
        pos = torch.arange(n, dtype=torch.float32)
        omega = 1.0 / (10000 ** (torch.arange(d // 2, dtype=torch.float32) / (d // 2)))
        ang = pos[:, None] * omega[None]
        emb = torch.cat([ang.sin(), ang.cos()], dim=1)  # (n, d)
        shape = [1, 1, 1, d]
        shape[axis] = n
        out.append(emb.view(shape).expand(*grid, d))
    return torch.cat(out, dim=-1).reshape(-1, dim)


class Block(nn.Module):
    def __init__(self, dim: int, heads: int, mlp_ratio: float = 4.0):
        super().__init__()
        self.n1 = nn.LayerNorm(dim)
        self.attn = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.n2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(
            nn.Linear(dim, int(dim * mlp_ratio)), nn.GELU(), nn.Linear(int(dim * mlp_ratio), dim)
        )

    def forward(self, x):
        h = self.n1(x)
        x = x + self.attn(h, h, h, need_weights=False)[0]
        return x + self.mlp(self.n2(x))


class ViT3D(nn.Module):
    def __init__(self, crop: int, patch: int, dim: int, depth: int, heads: int):
        super().__init__()
        self.grid = (crop // patch,) * 3
        self.embed = PatchEmbed3D(patch, dim)
        self.register_buffer("pos", sincos_3d(self.grid, dim), persistent=False)
        self.blocks = nn.ModuleList([Block(dim, heads) for _ in range(depth)])
        self.norm = nn.LayerNorm(dim)

    def forward(self, x, keep: torch.Tensor | None = None):
        """keep: (B, K) token indices to encode (context); None = all tokens."""
        tok = self.embed(x) + self.pos[None]
        if keep is not None:
            tok = torch.gather(tok, 1, keep[..., None].expand(-1, -1, tok.shape[-1]))
        for blk in self.blocks:
            tok = blk(tok)
        return self.norm(tok)


class Predictor(nn.Module):
    def __init__(self, dim: int, pred_dim: int, depth: int, heads: int, n_tokens: int, pos: torch.Tensor):
        super().__init__()
        self.inp = nn.Linear(dim, pred_dim)
        self.mask_token = nn.Parameter(torch.zeros(1, 1, pred_dim))
        self.pos_proj = nn.Linear(pos.shape[-1], pred_dim)
        self.register_buffer("pos", pos, persistent=False)
        self.blocks = nn.ModuleList([Block(pred_dim, heads) for _ in range(depth)])
        self.norm = nn.LayerNorm(pred_dim)
        self.out = nn.Linear(pred_dim, dim)
        nn.init.trunc_normal_(self.mask_token, std=0.02)

    def forward(self, ctx: torch.Tensor, ctx_idx: torch.Tensor, tgt_idx: torch.Tensor):
        b = ctx.shape[0]
        x = self.inp(ctx) + self.pos_proj(self.pos[ctx_idx])
        q = self.mask_token.expand(b, tgt_idx.shape[1], -1) + self.pos_proj(self.pos[tgt_idx])
        h = torch.cat([x, q], dim=1)
        for blk in self.blocks:
            h = blk(h)
        return self.out(self.norm(h[:, ctx.shape[1] :]))


# ---------------------------------------------------------------------------- masking
def block_masks(
    grid: tuple[int, int, int], n_targets: int, target_frac: tuple[float, float], context_frac: float, rng
):
    """I-JEPA style in 3-D: n_targets random blocks (each a target), context = the rest minus a random crop."""
    gd, gh, gw = grid
    n = gd * gh * gw
    all_idx = np.arange(n).reshape(grid)
    targets = []
    taken = np.zeros(grid, dtype=bool)
    for _ in range(n_targets):
        frac = rng.uniform(*target_frac)
        side = max(1, int(round((frac * n) ** (1 / 3))))
        sd, sh, sw = (min(side, gd), min(side, gh), min(side, gw))
        z, y, x = rng.integers(0, gd - sd + 1), rng.integers(0, gh - sh + 1), rng.integers(0, gw - sw + 1)
        blk = all_idx[z : z + sd, y : y + sh, x : x + sw].ravel()
        targets.append(blk)
        taken[z : z + sd, y : y + sh, x : x + sw] = True
    ctx_side = int(round((context_frac * n) ** (1 / 3)))
    cd, ch, cw = (min(ctx_side, gd), min(ctx_side, gh), min(ctx_side, gw))
    z, y, x = rng.integers(0, gd - cd + 1), rng.integers(0, gh - ch + 1), rng.integers(0, gw - cw + 1)
    ctx_mask = np.zeros(grid, dtype=bool)
    ctx_mask[z : z + cd, y : y + ch, x : x + cw] = True
    ctx = all_idx[ctx_mask & ~taken]
    tgt = np.unique(np.concatenate(targets))
    return ctx, tgt


# ---------------------------------------------------------------------------- data
class VolumeCrops(torch.utils.data.Dataset):
    def __init__(
        self,
        dataset: str,
        role: str,
        take: int | None,
        crop: int,
        spacing: float,
        modality: str,
        seed: int = 0,
    ):
        import pardesline as pl

        ds = pl.load(dataset)
        if take:
            ds = ds.take(take)
        self.samples = [s for s in ds if role in s.roles]
        self.role, self.crop, self.spacing, self.modality = role, crop, spacing, modality
        self.rng = np.random.default_rng(seed)
        self._cache: dict[int, np.ndarray] = {}

    def __len__(self):
        return len(self.samples)

    def _volume(self, i: int) -> np.ndarray:
        if i in self._cache:
            return self._cache[i]
        import SimpleITK as sitk

        img = self.samples[i].get(self.role).to_sitk()
        if img.GetNumberOfComponentsPerPixel() > 1:
            img = sitk.VectorIndexSelectionCast(img, 0)
        img = sitk.Cast(img, sitk.sitkFloat32)
        new_size = [
            max(self.crop, int(round(sz * sp / self.spacing)))
            for sz, sp in zip(img.GetSize(), img.GetSpacing())
        ]
        img = sitk.Resample(
            img,
            new_size,
            sitk.Transform(),
            sitk.sitkLinear,
            img.GetOrigin(),
            [self.spacing] * 3,
            img.GetDirection(),
            0.0,
        )
        arr = sitk.GetArrayFromImage(img)
        if self.modality == "ct":
            arr = np.clip(arr, -1000, 1000) / 1000.0
        else:
            arr = (arr - arr.mean()) / (arr.std() + 1e-6)
        self._cache[i] = arr.astype(np.float32)
        return self._cache[i]

    def __getitem__(self, i):
        v = self._volume(i)
        c = self.crop
        z = self.rng.integers(0, v.shape[0] - c + 1)
        y = self.rng.integers(0, v.shape[1] - c + 1)
        x = self.rng.integers(0, v.shape[2] - c + 1)
        return torch.from_numpy(v[z : z + c, y : y + c, x : x + c])[None]


class SyntheticVolumes(torch.utils.data.Dataset):
    """Blurred random blobs: enough to prove the loop runs and the loss falls."""

    def __init__(self, n: int, crop: int):
        self.n, self.crop = n, crop

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        rng = np.random.default_rng(i)
        v = rng.random((self.crop,) * 3).astype(np.float32)
        from scipy import ndimage

        v = ndimage.gaussian_filter(v, 3.0)
        v = (v - v.mean()) / (v.std() + 1e-6)
        return torch.from_numpy(v)[None]


# ---------------------------------------------------------------------------- training
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset")
    ap.add_argument("--role", default="ct")
    ap.add_argument("--modality", default="ct", choices=["ct", "mr"])
    ap.add_argument("--take", type=int)
    ap.add_argument("--spacing", type=float, default=1.5, help="isotropic resampling, mm")
    ap.add_argument("--crop", type=int, default=96)
    ap.add_argument("--patch", type=int, default=16)
    ap.add_argument("--dim", type=int, default=384)
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--heads", type=int, default=6)
    ap.add_argument("--pred-dim", type=int, default=192)
    ap.add_argument("--pred-depth", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--ema", type=float, nargs=2, default=(0.996, 1.0))
    ap.add_argument("--out", default="./runs/jepa3d")
    ap.add_argument("--smoke", action="store_true", help="synthetic data, tiny model, CPU")
    args = ap.parse_args()

    if args.smoke:
        args.crop, args.patch, args.dim, args.depth, args.heads = 32, 8, 96, 2, 2
        args.pred_dim, args.pred_depth, args.epochs, args.batch = 48, 1, 3, 4
        data = SyntheticVolumes(16, args.crop)
    else:
        if not args.dataset:
            raise SystemExit("--dataset is required (or --smoke)")
        data = VolumeCrops(args.dataset, args.role, args.take, args.crop, args.spacing, args.modality)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    loader = torch.utils.data.DataLoader(data, batch_size=args.batch, shuffle=True, drop_last=True)

    encoder = ViT3D(args.crop, args.patch, args.dim, args.depth, args.heads).to(device)
    target = copy.deepcopy(encoder).to(device)
    for p in target.parameters():
        p.requires_grad = False
    predictor = Predictor(
        args.dim,
        args.pred_dim,
        args.pred_depth,
        max(1, args.heads // 2),
        math.prod(encoder.grid),
        encoder.pos,
    ).to(device)
    params = list(encoder.parameters()) + list(predictor.parameters())
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.05)
    steps = args.epochs * len(loader)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=max(1, steps), pct_start=0.1)
    rng = np.random.default_rng(0)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    step = 0
    for epoch in range(args.epochs):
        t0, losses, stds = time.time(), [], []
        for x in loader:
            x = x.to(device)
            ctx_idx, tgt_idx = block_masks(
                encoder.grid, n_targets=4, target_frac=(0.15, 0.2), context_frac=0.85, rng=rng
            )
            ctx_idx = torch.as_tensor(ctx_idx, device=device)[None].expand(x.shape[0], -1)
            tgt_idx = torch.as_tensor(tgt_idx, device=device)[None].expand(x.shape[0], -1)
            with torch.no_grad():
                full = target(x)  # (B, N, dim), all tokens
                tgt = F.layer_norm(
                    torch.gather(full, 1, tgt_idx[..., None].expand(-1, -1, full.shape[-1])),
                    (full.shape[-1],),
                )
            ctx = encoder(x, keep=ctx_idx)
            pred = predictor(ctx, ctx_idx, tgt_idx)
            loss = F.smooth_l1_loss(pred, tgt)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            # EMA update of the target encoder
            m = args.ema[0] + (args.ema[1] - args.ema[0]) * min(1.0, step / max(1, steps))
            with torch.no_grad():
                for pt, pe in zip(target.parameters(), encoder.parameters()):
                    pt.mul_(m).add_(pe.detach(), alpha=1 - m)
            losses.append(loss.item())
            stds.append(float(tgt.std(dim=(0, 1)).mean()))  # collapse monitor: per-dim std of targets
            step += 1
        print(
            f"epoch {epoch:3d} loss {np.mean(losses):.4f} target-std {np.mean(stds):.3f} ({time.time() - t0:.0f}s)"
        )
        torch.save({"encoder": encoder.state_dict(), "args": vars(args)}, out / "encoder.pt")
    print(json.dumps({"final_loss": float(np.mean(losses)), "weights": str(out / "encoder.pt")}, indent=2))


if __name__ == "__main__":
    main()
