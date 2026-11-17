"""Generate docs/assets/social-preview.png (1280 x 640, GitHub's social card size).

    python docs/assets/make_social_preview.py

Logo glyph, wordmark, tagline, the three keywords, the install line and a strip
of five posters from docs/showcase. Upload the result in Settings -> General ->
Social preview. Needs Pillow only.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
SHOWCASE = HERE.parent / "showcase"
OUT = HERE / "social-preview.png"
BG, FG, ACCENT, GREEN = (21, 26, 36), (232, 236, 242), (240, 160, 90), (126, 231, 135)
POSTERS = [
    "jepa-latent-prediction.jpeg",
    "dinov3-gram-anchoring.jpeg",
    "ct-mr-rigid-registration.jpeg",
    "ransac-icp-bunny.jpeg",
    "pointnet-cbct-segmentation.jpeg",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for name in (
        "segoeui.ttf",
        "arial.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def letterbox(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGB")
    scale = min(w / img.width, h / img.height)
    resized = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), BG)
    canvas.paste(resized, ((w - resized.width) // 2, (h - resized.height) // 2))
    return canvas


def glyph(d: ImageDraw.ImageDraw, x: int, y: int, s: int = 72) -> None:
    """The point-cloud icon of docs/assets/icon.svg, drawn with Pillow."""
    d.rounded_rectangle((x, y, x + s, y + s), radius=16, fill=(30, 36, 48))
    k = s / 72
    for a, b in (((22, 54), (22, 18)), ((22, 54), (58, 54)), ((22, 54), (10, 66))):
        d.line((x + a[0] * k, y + a[1] * k, x + b[0] * k, y + b[1] * k), fill=(58, 68, 84), width=2)
    for cx, cy, r in (
        (30, 40, 3.2),
        (40, 33, 3.2),
        (49, 27, 3.2),
        (36, 46, 2.6),
        (45, 41, 2.6),
        (53, 36, 2.6),
        (27, 29, 2.2),
        (38, 23, 2.2),
        (50, 46, 2.2),
    ):
        d.ellipse((x + (cx - r) * k, y + (cy - r) * k, x + (cx + r) * k, y + (cy + r) * k), fill=ACCENT)


def main() -> None:
    w, h = 1280, 640
    canvas = Image.new("RGB", (w, h), BG)
    strip_h = 270
    tile_w = w // 5
    for i, name in enumerate(POSTERS):
        canvas.paste(
            letterbox(Image.open(SHOWCASE / name), tile_w - 8, strip_h), (i * tile_w + 4, h - strip_h - 8)
        )
    d = ImageDraw.Draw(canvas)
    glyph(d, 48, 44, 72)
    d.text((136, 40), "pardes", fill=FG, font=font(64))
    d.text((136 + d.textlength("pardes", font=font(64)), 40), "line", fill=ACCENT, font=font(64))
    d.text((48, 140), "3D computer vision and medical imaging in Python", fill=FG, font=font(36))
    d.text(
        (48, 196),
        "datasets in one line  ·  algorithms with defaults that work on real scans  ·  MCP for AI agents",
        fill=ACCENT,
        font=font(24),
    )
    d.text((48, 240), 'pip install "pardesline[all]"', fill=GREEN, font=font(30))
    d.text(
        (48, 300),
        "43 datasets  ·  73 algorithms  ·  Open3D / PyVista / SimpleITK  ·  Apache-2.0",
        fill=(160, 170, 185),
        font=font(22),
    )
    canvas.save(OUT, optimize=True)
    print(OUT, f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
