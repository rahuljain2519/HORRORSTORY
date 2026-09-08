"""Story generation via Ollama (free local LLM) or a cloud fallback.

Output format: a dict with keys:
  {
    "title": "छाया का साया",
    "hook": "वो दरवाज़ा... कभी ख़ुद से क्यों खुलता है?",
    "scenes": [
      {"id": 0, "narration": "हिंदी में डरावनी पंक्तियाँ...",
       "image_prompt": "ENGLISH cinematic prompt for the image", "image_seed": 0},
      ...
    ]
  }
"""
import json
import re
from pathlib import Path

import time
import requests

from config import OLLAMA_HOST, OLLAMA_MODEL, STORY_API_MODE, TEMPLATES_DIR, STORIES_DIR
from utils import log_info, log_error, save_json, clean_title

MAX_SCENES = 9          # images per story
SCENE_WORD_TARGET = 45  # ~ 40-45 Hindi words per scene -> ~35-45 secs narration each


def _load_prompt_template() -> str:
    tpl = TEMPLATES_DIR / "story_prompt.txt"
    return tpl.read_text(encoding="utf-8")


def _call_ollama(system: str, user: str, timeout=300) -> str:
    """Call Ollama's /api/generate (or /api/chat). Free & local."""
    url = f"{OLLAMA_HOST.rstrip('/')}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": user,
        "stream": False,
        "options": {"temperature": 0.85, "num_predict": 3200},
    }
    log_info(f"Calling Ollama model={OLLAMA_MODEL} ...")
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


_BLOCKLIST = ("aqa", "deep-research", "embedding", "imagen", "image", "tts",
              "audio", "slam", "segmenter", "veo", "veoverno")
_FAVOR_FLASH = ("flash", "2.0", "2.5", "nano", "mini", "lite")


def _discover_gemini_models(api_key: str) -> list[str]:
    """Ask the API which generateContent models this key can actually use.

    Returns model names ranked: flash/nano/lite variants first (fast+free),
    then the remaining gemini chat models. Non-text models are skipped.
    """
    try:
        r = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"?key={api_key}&pageSize=100",
            timeout=60,
        )
        r.raise_for_status()
        names = [m["name"].split("/")[-1] for m in r.json().get("models", [])]
    except Exception as e:  # noqa: BLE001
        log_info(f"Model discovery failed ({e}); using fallback list.")
        names = []

    text_models = [
        n for n in names
        if not any(b in n.lower() for b in _BLOCKLIST)
        and ("gemini" in n.lower() or "flash" in n.lower())
    ]
    if not text_models:
        text_models = names and [n for n in names if "gemini" in n.lower()] or names

    flashy = [n for n in text_models if any(f in n.lower() for f in _FAVOR_FLASH)]
    ranked = flashy + [n for n in text_models if n not in flashy]
    if ranked:
        log_info("Gemini models discovered: " + ", ".join(ranked))
    return ranked


def _call_gemini(system: str, user: str, timeout=300) -> str:
    """Call Google's free tier Gemini API (needs a free key - no charges).

    Auto-discovers the model names available to this key (naming differs by
    account/region), so no model needs to be configured. 503s mean the model
    is temporarily overloaded -> retried persistently with backoff.
    """
    from config import GOOGLE_AI_API_KEY, GEMINI_MODEL
    if not GOOGLE_AI_API_KEY:
        raise RuntimeError(
            "STORY_API_MODE=gemini needs GOOGLE_AI_API_KEY (free from "
            "aistudio.google.com/apikey)."
        )

    detected = _discover_gemini_models(GOOGLE_AI_API_KEY)
    candidates = []
    for m in (GEMINI_MODEL, "gemini-flash-latest"):
        if m and m not in candidates:
            candidates.append(m)
    candidates += detected

    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 4096},
    }

    # On 503/unavailable keep retrying for ~60s per model before moving on.
    last_err = None
    for model in candidates:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GOOGLE_AI_API_KEY}"
        )
        for attempt in range(1, 7):
            log_info(f"Calling Gemini model={model} (attempt {attempt}/6) ...")
            try:
                resp = requests.post(url, json=payload, timeout=timeout)
                if resp.status_code in (429, 503):
                    delay = 7 + attempt * 6
                    log_info(f"{model} busy ({resp.status_code}); retrying in {delay}s")
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if text.strip():
                    return text
            except (KeyError, IndexError) as e:
                last_err = f"Malformed response from {model}: {e}"
                log_info(str(last_err))
                break
            except requests.HTTPError as e:
                last_err = f"{model} failed: {e}"
                status = getattr(e.response, "status_code", None)
                if status in (400, 401, 403):
                    # Key/account-level errors won't change with a different model
                    raise RuntimeError(last_err) from e
                log_info(str(last_err))
                break

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def _call_pollinations_text(system: str, user: str, timeout=300) -> str:
    """Call Pollinations free text API. No API key required - usable on CI."""
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "model": "openai",
        "private": True,
    }
    log_info("Calling Pollinations text API (free, cloud)...")
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of model output (handles markdown fences)."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM output.")
    raw = text[start : end + 1]
    return json.loads(raw)


def _validate(data: dict) -> dict:
    if not data.get("title"):
        raise ValueError("Missing 'title'")
    scenes = data.get("scenes", [])
    if len(scenes) < 5:
        raise ValueError(f"Too few scenes ({len(scenes)}) - need >= 5")
    out_scenes = []
    for i, sc in enumerate(scenes[:MAX_SCENES]):
        narration = (sc.get("narration") or "").strip()
        image_prompt = (sc.get("image_prompt") or "").strip()
        if not narration or not image_prompt:
            continue
        out_scenes.append(
            {"id": i, "narration": narration, "image_prompt": image_prompt, "image_seed": i}
        )
    if len(out_scenes) < 5:
        raise ValueError("Not enough valid scenes after cleaning.")
    return {"title": data["title"].strip(), "hook": data.get("hook", "").strip(), "scenes": out_scenes}


def generate_story() -> dict:
    """Generate a Hindi horror story via configured backend."""
    template = _load_prompt_template()

    if STORY_API_MODE == "ollama":
        system = "तुम एक प्रसिद्ध हिंदी डरावनी कहानी लेखक हो। गहरा, मनोवैज्ञानिक और अलौकिक हॉरर लिखते हो।"
        user = template
        raw = _call_ollama(system, user)
    elif STORY_API_MODE == "gemini":
        system = "तुम एक प्रसिद्ध हिंदी डरावनी कहानी लेखक हो। केवल JSON आउटपुट दो।"
        user = template
        raw = _call_gemini(system, user)
    else:  # legacy 'cloud' -> try Pollinations free text API
        system = "तुम एक प्रसिद्ध हिंदी डरावनी कहानी लेखक हो। केवल JSON आउटपुट दो।"
        user = template
        raw = _call_pollinations_text(system, user)

    log_info("Raw story output received, parsing...")
    data = _validate(_extract_json(raw))

    title = clean_title(data["title"])
    out_path = STORIES_DIR / f"{title}.json"
    save_json(data, out_path)
    log_info(f"Story saved -> {out_path}")
    return data, out_path


if __name__ == "__main__":
    story, path = generate_story()
    print(f"Title: {story['title']}")
    print(f"Hook: {story['hook']}")
    print(f"Scenes: {len(story['scenes'])}")