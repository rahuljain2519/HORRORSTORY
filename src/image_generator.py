"""Image generation via Pollinations.ai (100% free, no API key).

Downloads one image per scene + a cover image.
"""
import random
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

from config import (
    IMAGES_DIR, POLLINATIONS_BASE, POLLINATIONS_REFERRER,
    VIDEO_WIDTH, VIDEO_HEIGHT,
)
from utils import log_info, log_error, clean_title

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_MODELS = ["flux", "turbo"]  # primary + lighter/cheaper fallback


@dataclass
class ImageSpec:
    prompt: str
    filename: str
    seed: int = 0


def _build_prompts(story: dict) -> list[ImageSpec]:
    title = clean_title(story["title"])
    specs = []
    cover = story.get("cover_prompt") or story["hook"]
    specs.append(ImageSpec(prompt=cover, filename=f"{title}_cover.jpg", seed=999))
    for sc in story["scenes"]:
        specs.append(
            ImageSpec(
                prompt=sc["image_prompt"],
                filename=f"{title}_scene{sc['id']:02d}.jpg",
                seed=sc.get("image_seed", sc["id"]),
            )
        )
    return specs


def _download(spec: ImageSpec, width: int, height: int) -> Path:
    """Download from Pollinations; sizing favours portrait for vertical videos.

    Batches the per-image retries nicely: tries each model, then backs off
    between attempts. No API key needed.
    """
    dest = IMAGES_DIR / spec.filename
    base = f"{POLLINATIONS_BASE}{quote(spec.prompt)}"
    last_err = None
    for model in _MODELS:
        for attempt in range(6):
            params = {
                "width": width,
                "height": height,
                "model": model,
                "nologo": "true",
                "seed": spec.seed,
                "referrer": POLLINATIONS_REFERRER,
            }
            try:
                r = requests.get(base, params=params, timeout=180, headers=_UA)
                r.raise_for_status()
                if len(r.content) < 10000:
                    raise RuntimeError("Response too small (likely placeholder)")
                dest.write_bytes(r.content)
                return dest
            except Exception as e:  # noqa: BLE001
                last_err = e
                delay = 10 + int(random.random() * 8) + 8 * attempt
                log_error(
                    f"Image attempt {attempt + 1}/{len(_MODELS) * 6} "
                    f"({model}) failed ({e}); sleeping {delay}s..."
                )
                time.sleep(delay)
    raise RuntimeError(f"Could not generate image for: {spec.filename} ({last_err})")


def generate_images(story: dict, portrait=True) -> list[Path]:
    """Download all scene images. Returns list of image paths (cover first)."""
    specs = _build_prompts(story)
    width, height = (VIDEO_WIDTH, VIDEO_HEIGHT) if portrait else (1920, 1080)
    paths = []
    for spec in specs:
        log_info(f"Generating image: {spec.filename}")
        p = _download(spec, width, height)
        paths.append(p)
    log_info(f"Done. Generated {len(paths)} images into {IMAGES_DIR}")
    return paths


if __name__ == "__main__":
    import json
    import sys
    from utils import load_json

    story_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if story_path is None:
        print("Usage: python image_generator.py <story.json>")
        sys.exit(1)
    s = load_json(story_path)
    images = generate_images(s)
    for i in images:
        print(i)