"""VAE anomaly detection on 2-D medical images: train on normal images, score any image.

    python vae_anomaly.py train --normal ./xrays/healthy --out ./runs/vae --epochs 150 --size 256 --latent 512
    python vae_anomaly.py score --weights ./runs/vae/vae.pt --images ./xrays/test --out ./scores
    python vae_anomaly.py score --weights ./runs/vae/vae.pt --images ./xrays/test --labels ./xrays/test_labels.csv --out ./scores
    python vae_anomaly.py --smoke                      # synthetic discs with/without a dark hole, CPU

score writes <name>_residual.png (smoothed |x - x_hat| heatmap), <name>_recon.png and scores.csv
(image score = mean of the top 1 % residual). labels.csv has two columns: file,label (1 = anomalous)
and triggers AUROC / AUPRC. Threshold suggestion = 99th percentile of the normal validation scores.
Needs torch and pillow.
"""

from __future__ import annotations

import argparse
import csv
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
class VAE(nn.Module):
    def __init__(self, size: int = 256, latent: int = 512, channels=(32, 64, 128, 256, 512)):
        super().__init__()
        enc, c_in = [], 1
        for c in channels:
            enc += [nn.Conv2d(c_in, c, 3, stride=2, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True)]
            c_in = c
        self.encoder = nn.Sequential(*enc)
        self.spatial = size // (2 ** len(channels))
        flat = channels[-1] * self.spatial * self.spatial
        self.mu = nn.Linear(flat, latent)
        self.logvar = nn.Linear(flat, latent)
        self.unflat = nn.Linear(latent, flat)
        dec, c_in = [], channels[-1]
        for c in reversed(channels[:-1]):
            dec += [
                nn.ConvTranspose2d(c_in, c, 4, stride=2, padding=1),
                nn.BatchNorm2d(c),
                nn.ReLU(inplace=True),
            ]
            c_in = c
        dec += [nn.ConvTranspose2d(c_in, 1, 4, stride=2, padding=1), nn.Sigmoid()]
        self.decoder = nn.Sequential(*dec)
        self.channels = channels

    def encode(self, x):
        h = self.encoder(x).flatten(1)
        return self.mu(h), self.logvar(h)

    def decode(self, z):
        h = self.unflat(z).view(-1, self.channels[-1], self.spatial, self.spatial)
        return self.decoder(h)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = mu + torch.exp(0.5 * logvar) * torch.randn_like(mu)
        return self.decode(z), mu, logvar


def vae_loss(x, recon, mu, logvar, beta: float):
    rec = F.mse_loss(recon, x, reduction="sum") / x.shape[0]
    kl = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp()) / x.shape[0]
    return rec + beta * kl, rec, kl


# ---------------------------------------------------------------------------- data
def load_gray(path: Path, size: int) -> np.ndarray:
    from PIL import Image

    img = Image.open(path).convert("L").resize((size, size), Image.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


class ImageFolder(torch.utils.data.Dataset):
    def __init__(self, folder: str | Path, size: int, augment: bool):
        self.files = sorted(
            p
            for p in Path(folder).iterdir()
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
        )
        self.size, self.augment = size, augment

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        x = load_gray(self.files[i], self.size)
        if self.augment:
            if np.random.rand() < 0.5:
                x = x[:, ::-1]
            x = np.clip(x * np.random.uniform(0.9, 1.1) + np.random.uniform(-0.05, 0.05), 0, 1)
        return torch.from_numpy(np.ascontiguousarray(x))[None]


class SyntheticDiscs(torch.utils.data.Dataset):
    """Normal: a bright disc with texture. Anomalous: the same with a dark hole (a 'cavity')."""

    def __init__(self, n: int, size: int, anomalous: bool, seed: int = 0):
        self.n, self.size, self.anomalous, self.seed = n, size, anomalous, seed

    def __len__(self):
        return self.n

    def make(self, i: int) -> np.ndarray:
        rng = np.random.default_rng(self.seed * 100000 + i)
        y, x = np.mgrid[0 : self.size, 0 : self.size]
        cx, cy, r = rng.uniform(0.4, 0.6, 2) * self.size, self.size * 0.5, self.size * rng.uniform(0.25, 0.35)
        img = 0.2 + 0.6 * (((x - cx) ** 2 + (y - cy) ** 2) < r**2)
        img += 0.05 * np.sin(x / 7.0 + rng.uniform(0, 6)) * np.sin(y / 9.0)
        if self.anomalous:
            hx, hy, hr = (
                cx + rng.uniform(-0.4, 0.4) * r,
                cy + rng.uniform(-0.4, 0.4) * r,
                r * rng.uniform(0.1, 0.2),
            )
            img[((x - hx) ** 2 + (y - hy) ** 2) < hr**2] = 0.1
        img += rng.normal(0, 0.02, img.shape)
        return np.clip(img, 0, 1).astype(np.float32)

    def __getitem__(self, i):
        return torch.from_numpy(self.make(i))[None]


# ---------------------------------------------------------------------------- commands
def train(model, data, device, epochs: int, lr: float, batch: int, beta_max: float, warmup: int, out: Path):
    loader = torch.utils.data.DataLoader(data, batch_size=batch, shuffle=True, drop_last=len(data) > batch)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for epoch in range(epochs):
        model.train()
        beta = beta_max * min(1.0, (epoch + 1) / max(1, warmup))  # KL warm-up against posterior collapse
        t0, tot, recs, kls = time.time(), [], [], []
        for x in loader:
            x = x.to(device)
            recon, mu, logvar = model(x)
            loss, rec, kl = vae_loss(x, recon, mu, logvar, beta)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot.append(loss.item())
            recs.append(rec.item())
            kls.append(kl.item())
        print(
            f"epoch {epoch:3d} beta {beta:.2f} loss {np.mean(tot):.1f} rec {np.mean(recs):.1f} kl {np.mean(kls):.1f} ({time.time() - t0:.0f}s)"
        )
    out.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model": model.state_dict(),
            "size": model.spatial * 2 ** len(model.channels),
            "latent": model.mu.out_features,
        },
        out / "vae.pt",
    )


@torch.no_grad()
def residual_maps(model, x: torch.Tensor, samples: int = 4, sigma: float = 3.0):
    """Average |x - x_hat| over several latent samples, then Gaussian-smooth."""
    from scipy import ndimage

    model.eval()
    res = torch.zeros_like(x)
    recon = None
    for _ in range(samples):
        r, _, _ = model(x)
        res += (x - r).abs()
        recon = r if recon is None else recon + r
    res, recon = (res / samples).cpu().numpy(), (recon / samples).cpu().numpy()
    smoothed = np.stack([ndimage.gaussian_filter(m[0], sigma) for m in res])
    return smoothed, recon[:, 0]


def image_score(residual: np.ndarray, top: float = 0.01) -> float:
    flat = np.sort(residual.ravel())
    return float(flat[-max(1, int(len(flat) * top)) :].mean())


def auroc(scores, labels) -> float:
    from scipy.stats import rankdata

    s, y = np.asarray(scores, float), np.asarray(labels).astype(bool)
    if y.all() or not y.any():
        return math.nan
    r = rankdata(s)
    return float((r[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum()))


def auprc(scores, labels) -> float:
    s, y = np.asarray(scores, float), np.asarray(labels).astype(bool)
    order = np.argsort(-s)
    y = y[order]
    tp = np.cumsum(y)
    precision = tp / np.arange(1, len(y) + 1)
    recall = tp / max(1, y.sum())
    return float(np.sum(np.diff(np.r_[0, recall]) * precision))


def cmd_score(model, data, files, device, out: Path, labels: dict[str, int] | None):
    from PIL import Image

    out.mkdir(parents=True, exist_ok=True)
    scores, names = [], []
    loader = torch.utils.data.DataLoader(data, batch_size=8)
    i = 0
    for x in loader:
        res, recon = residual_maps(model, x.to(device))
        for k in range(len(res)):
            name = Path(files[i]).stem if files else f"img{i:04d}"
            heat = (np.clip(res[k] / (res[k].max() + 1e-9), 0, 1) * 255).astype(np.uint8)
            Image.fromarray(heat).save(out / f"{name}_residual.png")
            Image.fromarray((recon[k] * 255).astype(np.uint8)).save(out / f"{name}_recon.png")
            scores.append(image_score(res[k]))
            names.append(name)
            i += 1
    with (out / "scores.csv").open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["file", "score"])
        w.writerows(zip(names, scores))
    report = {
        "images": len(scores),
        "score_median": float(np.median(scores)),
        "score_p99": float(np.percentile(scores, 99)),
    }
    if labels:
        y = [labels.get(n, labels.get(n + ".png", 0)) for n in names]
        report.update({"auroc": auroc(scores, y), "auprc": auprc(scores, y), "positives": int(sum(y))})
    print(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smoke", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("train")
    t.add_argument("--normal", required=True, help="folder of normal images")
    t.add_argument("--out", required=True)
    t.add_argument("--size", type=int, default=256)
    t.add_argument("--latent", type=int, default=512)
    t.add_argument("--epochs", type=int, default=150)
    t.add_argument("--batch", type=int, default=32)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--beta", type=float, default=1.0)
    t.add_argument("--warmup", type=int, default=10)
    s = sub.add_parser("score")
    s.add_argument("--weights", required=True)
    s.add_argument("--images", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--labels", help="csv file,label (1 = anomalous)")
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if args.smoke:
        size = 64
        model = VAE(size=size, latent=32, channels=(16, 32, 64)).to(device)
        train(
            model,
            SyntheticDiscs(64, size, anomalous=False),
            device,
            epochs=8,
            lr=1e-3,
            batch=16,
            beta_max=1.0,
            warmup=3,
            out=Path("./runs/vae_smoke"),
        )
        test = torch.utils.data.ConcatDataset(
            [SyntheticDiscs(16, size, False, seed=7), SyntheticDiscs(16, size, True, seed=9)]
        )
        labels = {f"img{i:04d}": int(i >= 16) for i in range(32)}
        report = cmd_score(model, test, None, device, Path("./runs/vae_smoke/scores"), labels)
        print("smoke test AUROC should be well above 0.5:", report.get("auroc"))
        return
    if args.cmd == "train":
        data = ImageFolder(args.normal, args.size, augment=True)
        model = VAE(size=args.size, latent=args.latent).to(device)
        train(model, data, device, args.epochs, args.lr, args.batch, args.beta, args.warmup, Path(args.out))
    elif args.cmd == "score":
        ckpt = torch.load(args.weights, map_location=device)
        model = VAE(size=ckpt["size"], latent=ckpt["latent"]).to(device)
        model.load_state_dict(ckpt["model"])
        data = ImageFolder(args.images, ckpt["size"], augment=False)
        labels = None
        if args.labels:
            with open(args.labels, newline="", encoding="utf-8") as fp:
                labels = {Path(r["file"]).stem: int(r["label"]) for r in csv.DictReader(fp)}
        cmd_score(model, data, [str(f) for f in data.files], device, Path(args.out), labels)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
