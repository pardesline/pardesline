"""Render a carousel HTML into a LinkedIn-ready PDF + per-slide PNGs.
Usage: conda run -n base python presentations/render.py presentations/carousel_w1.html
Outputs: same-name .pdf + presentations/preview/<name>_slideN.png
Each .slide div must be 1080x1350.
"""
import sys, os
from pathlib import Path
from playwright.sync_api import sync_playwright

html = Path(sys.argv[1]).resolve()
pdf_out = html.with_suffix(".pdf")
prev = html.parent / "preview"; prev.mkdir(exist_ok=True)
url = "file:///" + str(html).replace("\\", "/")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
    pg.goto(url, wait_until="load"); pg.wait_for_timeout(600)
    slides = pg.locator(".slide"); n = slides.count()
    for i in range(n):
        slides.nth(i).screenshot(path=str(prev / f"{html.stem}_slide{i+1}.png"))
    pg.pdf(path=str(pdf_out), width="1080px", height="1350px",
           print_background=True, prefer_css_page_size=True)
    b.close()
print(f"saved {pdf_out.name} ({n} slides) + {n} preview PNGs in presentations/preview/")
