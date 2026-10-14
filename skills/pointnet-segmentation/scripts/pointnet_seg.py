"""PointNet semantic segmentation: model, data loader, training, evaluation, inference.

Consumes the .npz contract written by make_point_dataset.py (points (N,6), labels (N,)).

    python pointnet_seg.py train --data ./hippo_points --epochs 100 --out ./runs/hippo
    python pointnet_seg.py eval  --data ./hippo_points --weights ./runs/hippo/best.pt
    python pointnet_seg.py infer --weights ./runs/hippo/best.pt --input scan.ply --output scan_labelled.ply

Needs torch (CUDA optional). The model is the original PointNet segmentation network
(Qi et al. 2017) with both T-Nets; swap in PointNet++ set abstraction for local detail.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError as exc:  # pragma: no cover - documented requirement
    raise SystemExit("this script needs PyTorch: pip install torch") from exc


# ---------------------------------------------------------------------------- model
class TNet(nn.Module):
    def __init__(self, k: int):
        super().__init__()
        self.k = k
        self.mlp = nn.Sequential(
            nn.Conv1d(k, 64, 1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Conv1d(64, 128, 1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Conv1d(128, 1024, 1),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Linear(256, k * k),
        )

    def forward(self, x):  # (B, k, N)
        g = self.mlp(x).max(dim=2)[0]
        m = self.fc(g).view(-1, self.k, self.k)
        return m + torch.eye(self.k, device=x.device).unsqueeze(0)  # residual on identity


class PointNetSeg(nn.Module):
    def __init__(self, num_classes: int, in_channels: int = 6):
        super().__init__()
        self.in_channels = in_channels
        self.t3 = TNet(3)
        self.mlp1 = nn.Sequential(
            nn.Conv1d(in_channels, 64, 1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Conv1d(64, 64, 1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
        )
        self.t64 = TNet(64)
        self.mlp2 = nn.Sequential(
            nn.Conv1d(64, 64, 1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Conv1d(64, 128, 1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Conv1d(128, 1024, 1),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Conv1d(1088, 512, 1),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Conv1d(512, 256, 1),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Conv1d(256, 128, 1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Conv1d(128, num_classes, 1),
        )

    def forward(self, x):  # x: (B, C, N), xyz in the first three channels
        xyz, extra = x[:, :3], x[:, 3:]
        t = self.t3(xyz)
        xyz = torch.bmm(t, xyz)  # input alignment (rotate normals with the same T)
        if extra.shape[1] >= 3:
            extra = torch.cat([torch.bmm(t, extra[:, :3]), extra[:, 3:]], dim=1)
        x = self.mlp1(torch.cat([xyz, extra], dim=1))
        a = self.t64(x)
        x = torch.bmm(a, x)  # feature alignment
        local = x  # (B, 64, N)
        g = self.mlp2(x).max(dim=2, keepdim=True)[0]  # (B, 1024, 1)
        x = torch.cat([local, g.expand(-1, -1, local.shape[2])], dim=1)  # (B, 1088, N)
        return self.head(x), a


def transform_regulariser(a: torch.Tensor) -> torch.Tensor:
    i = torch.eye(a.shape[1], device=a.device).unsqueeze(0)
    return ((i - torch.bmm(a, a.transpose(1, 2))) ** 2).sum(dim=(1, 2)).mean()


# ---------------------------------------------------------------------------- data
class NpzClouds(torch.utils.data.Dataset):
    def __init__(self, folder: str | Path, num_points: int, augment: bool, files=None):
        self.files = files if files is not None else sorted(Path(folder).glob("*.npz"))
        self.num_points = num_points
        self.augment = augment
        with np.load(self.files[0]) as z:
            self.classes = json.loads(str(z["classes"]))

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        with np.load(self.files[i]) as z:
            pts, lab = z["points"].astype(np.float32), z["labels"].astype(np.int64)
        idx = np.random.choice(len(pts), self.num_points, replace=len(pts) < self.num_points)
        pts, lab = pts[idx], lab[idx]
        if self.augment:
            theta = np.random.uniform(0, 2 * np.pi)
            c, s = np.cos(theta), np.sin(theta)
            rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)  # about the up axis (y)
            pts[:, :3] = pts[:, :3] @ rot.T
            if pts.shape[1] >= 6:
                pts[:, 3:6] = pts[:, 3:6] @ rot.T
            pts[:, :3] *= np.random.uniform(0.8, 1.25)
            pts[:, :3] += np.clip(np.random.normal(0, 0.01, pts[:, :3].shape), -0.05, 0.05)
        return torch.from_numpy(pts.T), torch.from_numpy(lab)


def class_weights(ds: NpzClouds, k: int) -> torch.Tensor:
    counts = np.zeros(k)
    for f in ds.files:
        with np.load(f) as z:
            counts += np.bincount(z["labels"], minlength=k)
    freq = counts / counts.sum()
    return torch.tensor(1.0 / np.log(1.2 + freq), dtype=torch.float32)


# ---------------------------------------------------------------------------- metrics
def iou_per_class(pred: np.ndarray, lab: np.ndarray, k: int) -> np.ndarray:
    out = np.full(k, np.nan)
    for c in range(k):
        p, t = pred == c, lab == c
        u = (p | t).sum()
        if u:
            out[c] = (p & t).sum() / u
    return out


@torch.no_grad()
def evaluate(model, loader, k, device):
    model.eval()
    ious, correct, total = [], 0, 0
    for pts, lab in loader:
        logits, _ = model(pts.to(device))
        pred = logits.argmax(1).cpu().numpy()
        lab = lab.numpy()
        for p, t in zip(pred, lab):
            ious.append(iou_per_class(p, t, k))
        correct += (pred == lab).sum()
        total += lab.size
    per_class = np.nanmean(np.stack(ious), axis=0)
    return {
        "accuracy": correct / total,
        "iou_per_class": per_class.tolist(),
        "mIoU": float(np.nanmean(per_class)),
    }


# ---------------------------------------------------------------------------- commands
def cmd_train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    files = sorted(Path(args.data).glob("*.npz"))
    n_val = max(1, int(len(files) * args.val_fraction))
    train_ds = NpzClouds(args.data, args.num_points, augment=True, files=files[n_val:])
    val_ds = NpzClouds(args.data, args.num_points, augment=False, files=files[:n_val])
    k = len(train_ds.classes)
    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=args.batch, shuffle=True, drop_last=len(train_ds) > args.batch
    )
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=args.batch)
    model = PointNetSeg(k, in_channels=6).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=20, gamma=0.5)
    weights = class_weights(train_ds, k).to(device)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    best = -1.0
    for epoch in range(args.epochs):
        model.train()
        t0, losses = time.time(), []
        for pts, lab in train_loader:
            pts, lab = pts.to(device), lab.to(device)
            logits, a = model(pts)
            loss = F.cross_entropy(
                logits, lab, weight=weights, label_smoothing=0.1
            ) + 1e-3 * transform_regulariser(a)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
        sched.step()
        metrics = evaluate(model, val_loader, k, device)
        print(
            f"epoch {epoch:3d} loss {np.mean(losses):.4f} val mIoU {metrics['mIoU']:.3f} acc {metrics['accuracy']:.3f} ({time.time() - t0:.0f}s)"
        )
        if metrics["mIoU"] > best:
            best = metrics["mIoU"]
            torch.save(
                {"model": model.state_dict(), "classes": train_ds.classes, "num_points": args.num_points},
                out / "best.pt",
            )
    print(f"best val mIoU {best:.3f}; weights in {out / 'best.pt'}")


def cmd_eval(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.weights, map_location=device)
    ds = NpzClouds(args.data, ckpt["num_points"], augment=False)
    model = PointNetSeg(len(ckpt["classes"])).to(device)
    model.load_state_dict(ckpt["model"])
    metrics = evaluate(model, torch.utils.data.DataLoader(ds, batch_size=8), len(ckpt["classes"]), device)
    metrics["classes"] = ckpt["classes"]
    print(json.dumps(metrics, indent=2))


@torch.no_grad()
def cmd_infer(args):
    import pardesline as pl
    from pardesline.object.arrays import write_ply

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.weights, map_location=device)
    model = PointNetSeg(len(ckpt["classes"])).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    cloud = pl.load(args.input)
    geo = cloud.to_open3d()
    xyz = np.asarray(geo.points)
    if len(geo.normals) != len(xyz):
        geo.estimate_normals()
    nrm = np.asarray(geo.normals)
    centroid = xyz.mean(0)
    scale = float(np.abs(xyz - centroid).max())
    feats = np.hstack([(xyz - centroid) / scale, nrm]).astype(np.float32)
    # all points, in chunks that fit the network's expected size
    n = ckpt["num_points"]
    labels = np.zeros(len(xyz), dtype=np.int64)
    order = np.random.permutation(len(xyz))
    for start in range(0, len(order), n):
        idx = order[start : start + n]
        if len(idx) < n:
            idx = np.concatenate([idx, np.random.choice(order, n - len(idx))])
        logits, _ = model(torch.from_numpy(feats[idx].T[None]).to(device))
        labels[idx] = logits.argmax(1)[0].cpu().numpy()
    out = write_ply(args.output, xyz, {"label": labels})
    counts = {ckpt["classes"][str(k)]: int((labels == k).sum()) for k in np.unique(labels)}
    print(json.dumps({"output": str(out), "counts": counts, "frame": cloud.frame.describe()}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--data", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--epochs", type=int, default=100)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--num-points", type=int, default=2048)
    t.add_argument("--val-fraction", type=float, default=0.2)
    e = sub.add_parser("eval")
    e.add_argument("--data", required=True)
    e.add_argument("--weights", required=True)
    i = sub.add_parser("infer")
    i.add_argument("--weights", required=True)
    i.add_argument("--input", required=True)
    i.add_argument("--output", required=True)
    args = ap.parse_args()
    {"train": cmd_train, "eval": cmd_eval, "infer": cmd_infer}[args.cmd](args)


if __name__ == "__main__":
    main()
