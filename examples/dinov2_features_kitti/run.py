"""Dense DINOv2 patch features on a KITTI camera frame (DINOv3 with the gated weights).

    pip install "pardesline[local]" torch transformers pillow
    python examples/dinov2_features_kitti/run.py            # writes feats/<frame>_pca.png

One left-camera frame is read out of the KITTI raw zip by HTTP Range and
``dinov3_features.py`` from the ``dinov3-dense-features`` skill extracts the
patch features of a frozen backbone and colours them by PCA. ``facebook/dinov2-small``
is used here because it downloads without an agreement; pass
``--model facebook/dinov3-vits16-pretrain-lvd1689m`` after accepting the licence on the Hub.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _skills import run

import pardesline as pl

HERE = Path(__file__).parent
drive = pl.load("kitti_raw_2011_09_26_drive_0001")
frame = next(s for s in drive if "image_left" in s.roles)
image = frame.image_left
run(
    "dinov3-dense-features",
    "dinov3_features.py",
    str(image.path),
    "--out",
    str(HERE / "feats"),
    "--model",
    "facebook/dinov2-small",
    "--size",
    "448",
)

# Side by side: the frame and the PCA-coloured patch features, upscaled to the frame size.
from PIL import Image

frame_img = Image.open(image.path).convert("RGB")
pca = (
    Image.open(HERE / "feats" / f"{Path(image.path).stem}_pca.png")
    .convert("RGB")
    .resize(frame_img.size, Image.NEAREST)
)
canvas = Image.new("RGB", (frame_img.width, frame_img.height * 2 + 8), "black")
canvas.paste(frame_img, (0, 0))
canvas.paste(pca, (0, frame_img.height + 8))
canvas.save(HERE / "dinov2_kitti.png")
print("wrote", HERE / "dinov2_kitti.png")
