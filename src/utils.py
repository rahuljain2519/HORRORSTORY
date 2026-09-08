"""Shared helpers: logging, JSON, text cleaning, request wrappers."""
import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

# On Windows, force UTF-8 for logging/output so Hindi characters don't crash.
if sys.platform == "win32" and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger("horror_story_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def log_info(msg):
    logger.info(msg)


def log_error(msg):
    logger.error(msg)


def find_devanagari_font():
    """Locate a Devanagari TTF on this system. Checks assets/fonts then common paths."""
    import config as cfg

    local = list(cfg.FONTS_DIR.glob("*.ttf")) + list(cfg.FONTS_DIR.glob("*.otf"))
    candidates = [str(p) for p in local] + [f for f in cfg.FONT_CANDIDATES if f not in [
        str(p) for p in local]]
    for f in candidates:
        if Path(f).exists():
            return str(f)
    return None


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log_info(f"Saved JSON: {path}")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_title(name: str) -> str:
    """Convert story name to safe filename."""
    name = re.sub(r"[^\w\s\u0900-\u097F]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return safe or "story"


def split_into_sentences(text: str):
    sentences = re.split(r"(?<=[।.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def http_get_json(url: str, params=None, timeout=60, retries=3, backoff=2.0):
    """Robust GET with retries."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"GET failed for {url}: {last_err}")


def pollinations_url(prompt: str, width=1024, height=1536, seed=None) -> str:
    """Build a Pollinations.ai image URL (free, no key)."""
    encoded = quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux&nologo=true"
    if seed is not None:
        url += f"&seed={seed}"
    return url


def add_cover_branding(title: str):
    """Small helper for hashtags / descriptions."""
    return f"{title}\n\n#horrorstory #hindihorror #bhayanakkahani #ghoststory #horrorshorts"