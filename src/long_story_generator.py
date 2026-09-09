"""Generate a LONG Hindi horror story (~15 min narration) for a single-image video.

Flow:
  1. Ask Gemini for an outline (title, hook, cover_prompt w/ ALL characters,
     characters list, chapter synopses).
  2. Expand each chapter one-by-one into a long narration (~1700-2000 chars).
  3. Save a story JSON:
       {
         "title", "hook", "cover_prompt", "characters",
         "chapters": [{"id","title","synopsis","narration"}]
       }

The cover_prompt is used for the SINGLE image that runs under the whole video.
"""
import json
import re
from pathlib import Path

from config import STORIES_DIR, TEMPLATES_DIR
from utils import log_info, save_json, clean_title
from story_generator import _call_gemini, _extract_json

TARGET_CHARS_PER_CHAPTER = (1700, 2100)  # Hindi chars -> ~2 min TTS each
MIN_CHAPTERS = 6
MAX_CHAPTERS = 8


def _load_outline_template() -> str:
    return (TEMPLATES_DIR / "long_story_outline.txt").read_text(encoding="utf-8")


def _as_text(data: dict) -> str:
    """Render outline data into context lines for chapter expansion."""
    chars = "; ".join(c.get("name", "") + " (" + c.get("description", "") + ")"
                      for c in data.get("characters", []))
    lines = [
        f"कहानी का शीर्षक: {data.get('title','')}",
        f"पात्र: {chars}",
    ]
    return "\n".join(lines)


def _expand_chapter(data: dict, ch: dict, is_last: bool) -> str:
    target = (TARGET_CHARS_PER_CHAPTER[0] + TARGET_CHARS_PER_CHAPTER[1]) // 2
    system = (
        "तुम एक प्रसिद्ध हिंदी डरावनी कहानी लेखक हो। "
        "विस्तृत, तनावपूर्ण और डरावना नैरेशन लिखते हो।"
    )
    user = f"""
{_as_text(data)}

अब अध्याय लिखो:
अध्याय {ch['id']}: {ch['title']}
सारांश/घटना: {ch['synopsis']}

नियम:
- अध्याय का पूरा नैरेशन लगभग {target} हिंदी अक्षरों (देवनागरी) में लिखो।
- (~15 मिनट की पूरी कहानी का यह एक अध्याय है।)
- घटनाएँ, संवाद, रहस्य और डरावना टेंशन विस्तार से।
- पात्रों के नाम एक जैसे रखो।
- {('यह कहानी का अंतिम अध्याय है - रहस्यमय समाधान/ट्विस्ट के साथ शानदार अंत।' if is_last else 'अध्याय के अंत में क्लिफहैंगर/सस्पेंस रखो ताकि अगला अध्याय जारी रहे।')}
- केवल अध्याय का नैरेशन टेक्स्ट ही लिखो। कोई शीर्षक, कोई JSON, कोई व्याख्या नहीं।
"""
    return _call_gemini(system, user)


def generate_long_story():
    """Generate and save a long story. Returns (story_dict, story_path)."""
    log_info("Generating LONG story outline via Gemini...")
    raw = _call_gemini(
        "तुम एक प्रसिद्ध हिंदी डरावनी कहानी लेखक हो। केवल JSON आउटपुट दो।",
        _load_outline_template(),
    )
    outline = _extract_json(raw)

    chapters_in = outline.get("chapters", [])
    chapters = []
    for i, ch in enumerate(chapters_in[:MAX_CHAPTERS]):
        if not ch.get("title"):
            continue
        chapters.append({
            "id": i,
            "title": str(ch["title"]).strip(),
            "synopsis": str(ch.get("synopsis", "")).strip(),
        })

    if len(chapters) < MIN_CHAPTERS:
        raise RuntimeError(f"Outline had too few chapters ({len(chapters)})")

    log_info(f"Expanding {len(chapters)} chapters into narrations...")
    expanded = []
    for i, ch in enumerate(chapters):
        log_info(f"Chapter {i + 1}/{len(chapters)}: {ch['title']} ...")
        narration = _expand_chapter(outline, ch, is_last=(i == len(chapters) - 1))
        narration = narration.strip()
        expanded.append({**ch, "narration": narration})
        log_info(f"  -> {len(narration)} chars")

    data = {
        "title": str(outline["title"]).strip(),
        "hook": str(outline.get("hook", "")).strip(),
        "cover_prompt": str(outline.get("cover_prompt", "")).strip(),
        "characters": outline.get("characters", []),
        "chapters": expanded,
    }

    title = clean_title(data["title"])
    out_path = STORIES_DIR / f"{title}.long.json"
    save_json(data, out_path)
    log_info(f"Long story saved -> {out_path}")
    return data, out_path


if __name__ == "__main__":
    story, path = generate_long_story()
    print(f"Title: {story['title']}")
    print(f"Hook: {story['hook']}")
    print(f"Chapters: {len(story['chapters'])}")
    for ch in story["chapters"]:
        print(f"  [{ch['id']}] {ch['title']} ({len(ch['narration'])} chars)")