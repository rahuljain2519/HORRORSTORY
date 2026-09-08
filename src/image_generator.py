"""Image generation via Pollinations.ai (100% free, no API key).

Downloads one image per scene + a cover image.
"""
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

from config import (IMAGES_DIR, POLLINATIONS_BASE, VIDEO_WIDTH, VIDEO_HEIGHT)
from utils import log_info, log_error, clean_title


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
    """Download from Pollinations; sizing favours portrait for vertical videos."""
    url = (
        f"{POLLINATIONS_BASE}"
        f"{quote(spec.prompt)}?width={width}&height={height}"
        f"&model=flux&nologo=true&seed={spec.seed}"
    )
    dest = IMAGES_DIR / spec.filename
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return dest
        except Exception as e:  # noqa: BLE001
            log_error(f"Image attempt {attempt + 1} failed ({e}); retrying...")
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"Could not generate image for: {spec.filename}")


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