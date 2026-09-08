"""Create up to 2 YouTube Shorts (<=60s) from the full story.

Strategy: pick the hook (scene 0) and the most dramatic later scene (peak),
cut vertical clips from the full video around those narration segments,
and re-encode to Shorts-friendly specs with an attention title overlay.
"""
from pathlib import Path

from moviepy.editor import VideoFileClip

import config as cfg
from config import SHORTS_DIR, SHORT_DURATION_MAX, SHORTS_PER_STORY
from utils import log_info, clean_title, find_devanagari_font


def _detect_scene_times(video_path: Path, story: dict):
    """Estimate each scene's [start, end] in the final video timeline.

    Uses narration durations probed from the mp3s that built the video,
    falling back to a text-length estimate if ffprobe is unavailable.
    """
    import subprocess

    ttl = clean_title(story["title"])
    starts = []
    cursor = 0.0

    def probe_length(name, text):
        p = cfg.AUDIO_DIR / f"{ttl}_{name}.mp3"
        if not p.exists():
            return max(cfg.IMAGE_DURATION, len(text) / 14.4)
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                text=True, timeout=15,
            ).strip()
            return float(out) + 0.4
        except Exception:  # noqa: BLE001
            return max(cfg.IMAGE_DURATION, len(text) / 14.4)

    cursor += probe_length("intro", story["hook"])
    for sc in story["scenes"]:
        d = probe_length(f"scene{sc['id']:02d}", sc["narration"])
        starts.append((cursor, cursor + d))
        cursor += d
    return starts


def _render_short(video_path: Path, start: float, end: float, out_path: Path, header: str):
    """Cut a window from the full video + overlay attention text."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy.editor import ImageClip, CompositeVideoClip

    seg = VideoFileClip(str(video_path)).subclip(start, min(end, start + SHORT_DURATION_MAX))
    if seg.duration > SHORT_DURATION_MAX:
        seg = seg.subclip(0, SHORT_DURATION_MAX)
    seg = seg.resize((cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT))

    # attention header overlay
    img = Image.new("RGBA", (cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = None
    custom_font = find_devanagari_font()
    if custom_font:
        try:
            font = ImageFont.truetype(custom_font, int(cfg.VIDEO_WIDTH * 0.05))
        except Exception:  # noqa: BLE001
            font = None
    if font:
        draw.text((3, 3), header, font=font, stroke_width=4, stroke_fill=(0, 0, 0),
                  fill=(255, 255, 255, 255))
        draw.text((0, 0), header, font=font, stroke_width=3, stroke_fill=(0, 0, 0),
                  fill=(220, 30, 30, 255))
    overlay = ImageClip(np.array(img)).set_duration(seg.duration)

    final = CompositeVideoClip([seg, overlay], size=(cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT))
    final.write_videofile(
        str(out_path), fps=cfg.FPS, codec="libx264", audio_codec="aac",
        preset="medium", threads=2, logger=None,
    )
    log_info(f"Short written: {out_path}")
    return out_path


def make_shorts(video_path: Path, story: dict) -> list[Path]:
    """Create SHORTS_PER_STORY shorts from the given full video."""
    ttl = clean_title(story["title"])
    timeline = _detect_scene_times(video_path, story)
    if not timeline:
        log_info("No timeline; skipping shorts.")
        return []

    # Short #1: the hook scene (scene 0) - front-loaded for retention
    hook_start, hook_end = timeline[0]
    # Short #2: the most dramatic scene (the final / twist scene)
    peak_start, peak_end = timeline[-1]

    plan = [
        (hook_start, hook_end, "🕯️ कहानी शुरू होती है..."),
        (peak_start, peak_end, "😱 अंत आपको चौंका देगा!"),
    ][:SHORTS_PER_STORY]

    out_files = []
    for i, (s, e, header) in enumerate(plan, start=1):
        out = SHORTS_DIR / f"{ttl}_short{i}.mp4"
        _render_short(video_path, s, e, out, header)
        out_files.append(out)
    return out_files


if __name__ == "__main__":
    import sys
    from utils import load_json

    story = load_json(Path(sys.argv[1]))
    vid = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if vid is None:
        full = sorted(cfg.FULL_VIDEOS_DIR.glob(f"{clean_title(story['title'])}_full.mp4"))
        vid = full[-1] if full else None
    if vid is None:
        raise SystemExit("No video to make shorts from")
    shorts = make_shorts(vid, story)
    for s in shorts:
        print(s)