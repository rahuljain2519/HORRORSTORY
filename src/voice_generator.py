"""Voice narration via edge-tts (Microsoft Edge neural voices - 100% free).

Generates one mp3 per scene plus an 'intro' clip (title hook narration).
edge-tts does not need an API key and works on GitHub Actions runners.
"""
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

import edge_tts

from config import AUDIO_DIR, VOICE_NAME, VOICE_RATE, VOICE_VOLUME
from utils import log_info, clean_title


@dataclass
class NarrationClip:
    path: Path
    text: str
    duration: float  # seconds (filled later)


async def _synth(text, out_path: Path) -> None:
    """Retry once on failure; edge-tts can 403 transiently from cloud IPs."""
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, VOICE_NAME, rate=VOICE_RATE, volume=VOICE_VOLUME)
            await communicate.save(str(out_path))
            return
        except Exception as e:  # noqa: BLE001
            log_info(f"TTS attempt {attempt + 1}/3 failed ({e}); retrying...")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"edge-tts could not synthesize: {text[:60]}...")


def _estimate_duration(mp3_path: Path, text: str) -> float:
    """Duration via ffprobe; falls back to a text-based estimate on failure."""
    import subprocess
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)]
        out = subprocess.check_output(cmd, text=True, timeout=20).strip()
        return float(out)
    except Exception:  # noqa: BLE001
        # Hindi TTS ~ 14.4 chars/sec
        return max(2.0, len(text) / 14.4)


async def generate_voice(story: dict) -> list[NarrationClip]:
    """Create narration clips for intro hook + each scene."""
    title = clean_title(story["title"])
    clips: list[NarrationClip] = []

    intro_text = f"{story['hook']}"
    intro_path = AUDIO_DIR / f"{title}_intro.mp3"
    await _synth(intro_text, intro_path)
    clips.append(NarrationClip(path=intro_path, text=intro_text, duration=_estimate_duration(intro_path, intro_text)))

    for sc in story["scenes"]:
        text = sc["narration"]
        path = AUDIO_DIR / f"{title}_scene{sc['id']:02d}.mp3"
        await _synth(text, path)
        clips.append(NarrationClip(path=path, text=text, duration=_estimate_duration(path, text)))

    for c in clips:
        log_info(f"Narration clip: {c.path.name} ({c.duration:.1f}s)")
    log_info(f"Generated {len(clips)} narration clips in {AUDIO_DIR}")
    return clips


def run_generate_voice(story: dict) -> list[NarrationClip]:
    return asyncio.run(generate_voice(story))


if __name__ == "__main__":
    import sys
    from utils import load_json

    story = load_json(Path(sys.argv[1])) if len(sys.argv) > 1 else None
    if story is None:
        print("Usage: python voice_generator.py <story.json>")
        sys.exit(1)
    clips = run_generate_voice(story)
    for c in clips:
        print(c.path, round(c.duration, 2))