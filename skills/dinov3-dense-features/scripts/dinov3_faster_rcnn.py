"""Frozen DINOv3 backbone + ViTDet simple feature pyramid + torchvision Faster R-CNN.

The recipe of the pericardial-effusion detector: 300 M frozen parameters, ~25 M
trainable (pyramid, RPN, RoI heads), focal-style class balance through sampling,
NMS 0.5. Dataset: COCO-format JSON (images, annotations with bbox [x, y, w, h],
category_id) and an image folder - the format every labelling tool exports.

    python dinov3_faster_rcnn.py train --images ./echo --ann ./echo/train.json --val-ann ./echo/val.json --out ./runs/effusion
    python dinov3_faster_rcnn.py eval  --images ./echo --ann ./echo/val.json --weights ./runs/effusion/best.pt
    python dinov3_faster_rcnn.py infer --weights ./runs/effusion/best.pt --image frame.png

Needs torch, torchvision, transformers, pycocotools (for mAP). Weights gated on the Hub.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import OrderedDict
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torchvision
    from torchvision.models.detection import FasterRCNN
    from torchvision.models.detection.anchor_utils import AnchorGenerator
    from torchvision.ops import MultiScaleRoIAlign
except ImportError as exc:  # pragma: no cover
    raise SystemExit("this script needs torch and torchvision") from exc

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


class FrozenDinoPyramid(nn.Module):
    """DINOv3 patch tokens (stride 16) -> P2 (1/4), P3 (1/8), P4 (1/16), P5 (1/32), 256 channels each."""

    def __init__(self, model_name: str, out_channels: int = 256):
        super().__init__()
        from transformers import AutoModel

        self.backbone = AutoModel.from_pretrained(model_name)
        for p in self.backbone.parameters():
            p.requires_grad = False
        self.backbone.eval()
        d = self.backbone.config.hidden_size
        self.patch = getattr(self.backbone.config, "patch_size", 16)
        self.registers = getattr(self.backbone.config, "num_register_tokens", 0)
        self.out_channels = out_channels
        self.p2 = nn.Sequential(
            nn.ConvTranspose2d(d, d // 2, 2, 2), nn.GELU(), nn.ConvTranspose2d(d // 2, out_channels, 2, 2)
        )
        self.p3 = nn.Sequential(nn.ConvTranspose2d(d, out_channels, 2, 2))
        self.p4 = nn.Conv2d(d, out_channels, 1)
        self.p5 = nn.Sequential(nn.MaxPool2d(2), nn.Conv2d(d, out_channels, 1))
        self.smooth = nn.ModuleList([nn.Conv2d(out_channels, out_channels, 3, padding=1) for _ in range(4)])

    def train(self, mode: bool = True):
        super().train(mode)
        self.backbone.eval()  # the backbone never leaves eval mode (frozen BN/LayerNorm statistics)
        return self

    def forward(self, x: torch.Tensor) -> OrderedDict:
        b, _, h, w = x.shape
        with torch.no_grad():
            tokens = self.backbone(pixel_values=x).last_hidden_state
        gh, gw = h // self.patch, w // self.patch
        fmap = (
            tokens[:, 1 + self.registers : 1 + self.registers + gh * gw]
            .transpose(1, 2)
            .reshape(b, -1, gh, gw)
        )
        feats = [self.p2(fmap), self.p3(fmap), self.p4(fmap), self.p5(fmap)]
        return OrderedDict((f"p{i + 2}", self.smooth[i](f)) for i, f in enumerate(feats))


def build_model(model_name: str, num_classes: int, size: int) -> FasterRCNN:
    backbone = FrozenDinoPyramid(model_name)
    anchors = AnchorGenerator(sizes=((32,), (64,), (128,), (256,)), aspect_ratios=((0.5, 1.0, 2.0),) * 4)
    roi = MultiScaleRoIAlign(featmap_names=["p2", "p3", "p4", "p5"], output_size=7, sampling_ratio=2)
    return FasterRCNN(
        backbone,
        num_classes=num_classes,  # background + K
        rpn_anchor_generator=anchors,
        box_roi_pool=roi,
        min_size=size,
        max_size=size,
        image_mean=MEAN,
        image_std=STD,
        rpn_pre_nms_top_n_train=2000,
        rpn_post_nms_top_n_train=1000,
        rpn_pre_nms_top_n_test=1000,
        rpn_post_nms_top_n_test=256,
        rpn_nms_thresh=0.7,
        box_nms_thresh=0.5,
        box_detections_per_img=20,
    )


class CocoBoxes(torch.utils.data.Dataset):
    def __init__(self, images: str, ann: str, size: int, train: bool):
        self.root = Path(images)
        data = json.loads(Path(ann).read_text(encoding="utf-8"))
        self.images = {im["id"]: im for im in data["images"]}
        self.by_image: dict[int, list] = {i: [] for i in self.images}
        for a in data["annotations"]:
            self.by_image[a["image_id"]].append(a)
        self.ids = sorted(self.images)
        self.cats = sorted({c["id"] for c in data["categories"]})
        self.cat_to_label = {c: i + 1 for i, c in enumerate(self.cats)}
        self.size = size
        self.train = train

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        from PIL import Image

        info = self.images[self.ids[i]]
        img = Image.open(self.root / info["file_name"]).convert("RGB")
        w, h = img.size
        s = self.size / max(w, h)
        nw, nh = max(16, int(round(w * s / 16)) * 16), max(16, int(round(h * s / 16)) * 16)
        img = img.resize((nw, nh))
        sx, sy = nw / w, nh / h
        boxes, labels = [], []
        for a in self.by_image[self.ids[i]]:
            x, y, bw, bh = a["bbox"]
            boxes.append([x * sx, y * sy, (x + bw) * sx, (y + bh) * sy])
            labels.append(self.cat_to_label[a["category_id"]])
        x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1)
        if self.train and np.random.rand() < 0.5:  # photometric only: geometry comes from the frozen backbone
            x = (x * np.random.uniform(0.8, 1.2)).clamp(0, 1)
        target = {
            "boxes": torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4),
            "labels": torch.tensor(labels, dtype=torch.int64),
            "image_id": torch.tensor(self.ids[i]),
            "scale": torch.tensor([sx, sy]),
        }
        return x, target


def collate(batch):
    return tuple(zip(*batch))


@torch.no_grad()
def evaluate_map(model, loader, device, ds: CocoBoxes, ann_path: str) -> dict:
    """COCO mAP through pycocotools; falls back to AP50 by greedy matching when it is missing."""
    model.eval()
    dets = []
    for images, targets in loader:
        outputs = model([im.to(device) for im in images])
        for o, t in zip(outputs, targets):
            sx, sy = t["scale"].tolist()
            for box, score, label in zip(o["boxes"].cpu(), o["scores"].cpu(), o["labels"].cpu()):
                x1, y1, x2, y2 = box.tolist()
                dets.append(
                    {
                        "image_id": int(t["image_id"]),
                        "category_id": ds.cats[int(label) - 1],
                        "bbox": [x1 / sx, y1 / sy, (x2 - x1) / sx, (y2 - y1) / sy],
                        "score": float(score),
                    }
                )
    try:
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval

        gt = COCO(ann_path)
        dt = gt.loadRes(dets) if dets else None
        if dt is None:
            return {"mAP": 0.0, "AP50": 0.0}
        ev = COCOeval(gt, dt, "bbox")
        ev.evaluate()
        ev.accumulate()
        ev.summarize()
        return {"mAP": float(ev.stats[0]), "AP50": float(ev.stats[1]), "detections": len(dets)}
    except ImportError:
        return {"detections": len(dets), "note": "install pycocotools for mAP"}


def cmd_train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_ds = CocoBoxes(args.images, args.ann, args.size, train=True)
    val_ds = CocoBoxes(args.images, args.val_ann, args.size, train=False)
    model = build_model(args.model, len(train_ds.cats) + 1, args.size).to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    print(f"trainable parameters: {sum(p.numel() for p in params) / 1e6:.1f} M (backbone frozen)")
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=args.batch, shuffle=True, collate_fn=collate, num_workers=2
    )
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=args.batch, collate_fn=collate, num_workers=2)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    best = -1.0
    for epoch in range(args.epochs):
        model.train()
        t0, losses = time.time(), []
        for images, targets in train_loader:
            images = [im.to(device) for im in images]
            targets = [{k: v.to(device) for k, v in t.items() if k in ("boxes", "labels")} for t in targets]
            loss_dict = model(images, targets)
            loss = sum(loss_dict.values())
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 10.0)
            opt.step()
            losses.append(loss.item())
        sched.step()
        metrics = evaluate_map(model, val_loader, device, val_ds, args.val_ann)
        print(f"epoch {epoch:3d} loss {np.mean(losses):.3f} {metrics} ({time.time() - t0:.0f}s)")
        score = metrics.get("AP50", -1.0)
        if score > best:
            best = score
            torch.save(
                {
                    "model": model.state_dict(),
                    "cats": train_ds.cats,
                    "size": args.size,
                    "backbone": args.model,
                },
                out / "best.pt",
            )
    print(f"best AP50 {best:.3f}; weights in {out / 'best.pt'}")


def cmd_eval(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.weights, map_location=device)
    ds = CocoBoxes(args.images, args.ann, ckpt["size"], train=False)
    model = build_model(ckpt["backbone"], len(ckpt["cats"]) + 1, ckpt["size"]).to(device)
    model.load_state_dict(ckpt["model"])
    print(
        json.dumps(
            evaluate_map(
                model, torch.utils.data.DataLoader(ds, batch_size=4, collate_fn=collate), device, ds, args.ann
            ),
            indent=2,
        )
    )


@torch.no_grad()
def cmd_infer(args):
    from PIL import Image

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.weights, map_location=device)
    model = build_model(ckpt["backbone"], len(ckpt["cats"]) + 1, ckpt["size"]).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    img = Image.open(args.image).convert("RGB")
    x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1).to(device)
    o = model([x])[0]
    dets = [
        {"box": b.tolist(), "score": float(s), "category": ckpt["cats"][int(l) - 1]}
        for b, s, l in zip(o["boxes"], o["scores"], o["labels"])
        if s >= args.threshold
    ]
    print(json.dumps(dets, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("train", "eval"):
        p = sub.add_parser(name)
        p.add_argument("--images", required=True)
        p.add_argument("--ann", required=True)
        if name == "train":
            p.add_argument("--val-ann", required=True)
            p.add_argument("--out", required=True)
            p.add_argument("--model", default="facebook/dinov3-vitl16-pretrain-lvd1689m")
            p.add_argument("--size", type=int, default=512)
            p.add_argument("--epochs", type=int, default=30)
            p.add_argument("--batch", type=int, default=4)
            p.add_argument("--lr", type=float, default=1e-4)
        else:
            p.add_argument("--weights", required=True)
    i = sub.add_parser("infer")
    i.add_argument("--weights", required=True)
    i.add_argument("--image", required=True)
    i.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()
    {"train": cmd_train, "eval": cmd_eval, "infer": cmd_infer}[args.cmd](args)


if __name__ == "__main__":
    main()
