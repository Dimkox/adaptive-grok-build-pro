#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path("/home/pall/grok-projects/adaptive-grok-build-pro")
PROJECT = ROOT / "side-projects" / "seo-landings" / "winston-wolfe-pulp-fiction-v2"
IMAGES = PROJECT / "images"
SOURCE = IMAGES / "_source"
SESSION = Path(
    "/home/pall/.grok/sessions/%2Fhome%2Fpall%2Fgrok-projects%2Fadaptive-grok-build-pro"
    "/01a0bcfb-f263-7a82-bad6-a4cfec0b0765/images"
)
WIDTHS = (320, 640, 768, 1024, 1280, 1920)
MASTERS = {
    "hero": SESSION / "1.jpg",
    "method": SESSION / "2.jpg",
}


def sha12(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def save_avif(image: Image.Image, path: Path) -> None:
    errors: list[str] = []
    try:
        image.save(path, "AVIF", quality=52)
        return
    except Exception as exc:
        errors.append(f"PIL AVIF: {exc}")
    try:
        import pillow_heif

        pillow_heif.register_avif_opener()
        image.save(path, "AVIF", quality=52)
        return
    except Exception as exc:
        errors.append(f"pillow_heif: {exc}")
    raise SystemExit("AVIF encoder missing; BLOCKER. " + " | ".join(errors))


def family(name: str, src: Path) -> str:
    data = src.read_bytes()
    digest = sha12(data)
    SOURCE.mkdir(parents=True, exist_ok=True)
    (SOURCE / f"{name}.jpg").write_bytes(data)
    master = Image.open(src).convert("RGB")
    for width in WIDTHS:
        height = max(1, round(master.height * (width / master.width)))
        resized = master.resize((width, height), Image.Resampling.LANCZOS)
        base = IMAGES / f"{name}.{digest}-{width}"
        resized.save(base.as_posix() + ".jpg", "JPEG", quality=76, optimize=True, progressive=True)
        resized.save(base.as_posix() + ".webp", "WEBP", quality=76, method=6)
        save_avif(resized, Path(base.as_posix() + ".avif"))
    print(f"{name} digest={digest} master={master.size}")
    return digest


def favicon() -> None:
    size = 96
    image = Image.new("RGB", (size, size), (11, 9, 8))
    draw = ImageDraw.Draw(image)
    gold = (212, 168, 67)
    stroke = 8
    left = [(18, 22), (30, 76), (42, 22)]
    right = [(42, 22), (54, 76), (66, 22)]
    draw.line(left, fill=gold, width=stroke, joint="miter")
    draw.line(right, fill=gold, width=stroke, joint="miter")
    draw.rectangle((8, 8, size - 9, size - 9), outline=gold, width=3)
    PROJECT.mkdir(parents=True, exist_ok=True)
    image.save(PROJECT / "favicon.png", "PNG")
    print("favicon 96x96")


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    for leftover in IMAGES.glob("hero.*"):
        leftover.unlink()
    for leftover in IMAGES.glob("method.*"):
        leftover.unlink()
    for name, src in MASTERS.items():
        if not src.is_file():
            raise SystemExit(f"missing master {src}")
        family(name, src)
    favicon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
