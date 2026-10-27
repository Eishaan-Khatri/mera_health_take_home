"""Build degraded copies of the 8 tuning reports, to test robustness to worse scans and photos.

Usage: python experiments/make_stress.py   -> experiments/stress/<kind>/report_XX.(pdf|jpg)

Needs Pillow (pip install pillow); extract.py itself has no dependencies. Every page is rendered
at 150 DPI (or loaded, for photos), degraded with a fixed seed, and saved in the original format:
PDFs stay (image-only) PDFs, so multi-page report_11 stays two pages and extract.py still renders
them at its own DPI; photos stay JPGs. The labels for report_XX apply unchanged to every copy.
"""
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "stress"
TUNING = ["01", "02", "03", "05", "06", "08", "09", "11"]
RENDER_DPI = 150


def low_res(im, rng):
    """About 40 DPI worth of pixels, scaled back up: a low-resolution scan or a heavily resized photo."""
    w, h = im.size
    return im.resize((int(w * 0.27), int(h * 0.27)), Image.BILINEAR).resize((w, h), Image.BILINEAR)


def rotate(im, rng):
    return im.rotate(rng.choice([-1, 1]) * 4, resample=Image.BICUBIC, expand=True, fillcolor="white")


def blur(im, rng):
    return im.filter(ImageFilter.GaussianBlur(radius=2.2))


def jpeg(im, rng):
    return im  # the damage is done when saving at quality 12, see QUALITY


def phone(im, rng):
    """Phone photo of a printout: slight tilt, uneven light with a shadow band, sensor noise, soft focus."""
    im = im.rotate(rng.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True, fillcolor=(205, 200, 190))
    w, h = im.size
    shade = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(shade)
    for x in range(w):  # light falls off from right to left
        draw.line([(x, 0), (x, h)], fill=int(170 + 85 * x / w))
    x0 = int(w * rng.uniform(0.15, 0.35))
    draw.rectangle([0, 0, x0, h], fill=120)  # a hand/phone shadow over the left part
    im = Image.composite(im, Image.new("RGB", (w, h), "black"), shade.filter(ImageFilter.GaussianBlur(25)))
    im = ImageEnhance.Contrast(im).enhance(0.8)
    noise = Image.effect_noise((w, h), 18).convert("RGB")
    im = Image.blend(im, noise, 0.08)
    return im.filter(ImageFilter.GaussianBlur(radius=1.0))


KINDS = {"low_res": low_res, "rotate": rotate, "blur": blur, "jpeg": jpeg, "phone": phone}
QUALITY = {"jpeg": 12, "phone": 55}  # JPEG quality when saving; others use 85


def pages(path):
    if path.suffix.lower() != ".pdf":
        return [Image.open(path).convert("RGB")]
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", str(RENDER_DPI), "-png", str(path), str(Path(d) / "p")],
                       check=True, capture_output=True)
        return [Image.open(p).convert("RGB") for p in sorted(Path(d).glob("p*.png"))]


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for kind, fn in KINDS.items():
        (OUT / kind).mkdir(parents=True)
        for rid in TUNING:
            src = next((ROOT / "reports").glob(f"report_{rid}.*"))
            rng = random.Random(f"{kind}-{rid}")
            imgs = [fn(im, rng) for im in pages(src)]
            q = QUALITY.get(kind, 85)
            if src.suffix.lower() == ".pdf":
                # round-trip every page through JPEG first so the quality loss is in the PDF too
                with tempfile.TemporaryDirectory() as d:
                    for i, im in enumerate(imgs):
                        im.save(Path(d) / f"{i}.jpg", quality=q)
                    imgs = [Image.open(Path(d) / f"{i}.jpg").convert("RGB") for i in range(len(imgs))]
                    imgs[0].save(OUT / kind / f"report_{rid}.pdf", save_all=True, append_images=imgs[1:],
                                 resolution=RENDER_DPI)
            else:
                imgs[0].save(OUT / kind / f"report_{rid}.jpg", quality=q)
        print(f"{kind}: {len(TUNING)} reports")


if __name__ == "__main__":
    main()
