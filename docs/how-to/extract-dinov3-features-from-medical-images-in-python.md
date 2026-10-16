---
title: How to extract DINOv3 features from medical images in Python (DINOv2 and DINOv3 dense patch features)
description: Extract dense DINOv3 or DINOv2 patch features from ultrasound frames, X-rays, CT slices or camera images in Python with a frozen backbone, colour them by PCA, save them for a detection or segmentation head; gated DINOv3 weights vs open DINOv2, image sizes, grayscale inputs.
---

# How to extract DINOv3 features from medical images in Python

A frozen DINOv3 (or DINOv2) backbone turns an image into a grid of patch embeddings that already separate tissue, bone, instrument and background without any medical training. The reference script extracts them, colours them by PCA so you can see what the model sees, and saves them for a head.

```bash
pip install "pardesline[local]" torch transformers pillow
python skills/dinov3-dense-features/scripts/dinov3_features.py frame.png --out ./feats --model facebook/dinov2-small --size 448
python skills/dinov3-dense-features/scripts/dinov3_features.py ./echo_frames --out ./feats --model facebook/dinov3-vits16-pretrain-lvd1689m
```

Output per image: `<name>.npz` with `patches (H/p, W/p, d) float16`, `cls (d,)`, the grid and the size, and `<name>_pca.png`. DINOv2 weights download without an agreement; DINOv3 weights are gated: accept the licence on the Hub, then `huggingface-cli login`. Grayscale images are replicated to three channels; `--size` is rounded to the patch size (14 for DINOv2, 16 for DINOv3).

The [KITTI example](../examples.md#dinov2_features_kitti) runs it on a camera frame read out of the KITTI zip by HTTP Range:

![KITTI camera frame above its PCA-coloured DINOv2 patch features](https://raw.githubusercontent.com/pardesline/pardesline/main/examples/dinov2_features_kitti/dinov2_kitti.png)

## From a pardesline dataset

```python
import pardesline as pl

frame = next(s for s in pl.load("kitti_raw_2011_09_26_drive_0001") if "image_left" in s.roles)
image = frame.image_left  # an Image object: image.path is the PNG
```

Volumes: extract per slice (`vol.to_numpy()[z]` to PNG) or use the 3D route ([JEPA](../models/jepa.md)) when you need volumetric features.

## A head on top

[`dinov3_faster_rcnn.py`](https://github.com/pardesline/pardesline/blob/main/skills/dinov3-dense-features/scripts/dinov3_faster_rcnn.py) puts a Faster R-CNN detection head on the frozen backbone (the echocardiography use case of the [DINOv3 guide](../models/dinov3.md)); a linear or small convolutional head on the patch grid gives a segmentation. Keep the backbone frozen first: it is the point of the method, and it trains in minutes on CPU for small datasets.

## Coming

One-line model access (`pl.load_model("dinov3")`, `pl.run(model, dataset)`) through the [model registry](../models/index.md); this page's commands keep working.

Related: [DINOv3 model page](../models/dinov3.md) · [Models](../models/index.md)
