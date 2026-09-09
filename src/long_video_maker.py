"""Assemble a 15-minute long story video from ONE image + long narration.

Single 16:9 image under the whole video with slow Ken Burns motion, rolling
subtitle text, chapter-by-chapter narration audio, and background music.

Targets ~15 min runtime for long-form YouTube uploads.
"""
import math
from pathlib import Path

import numpy as np
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    concatenate_audioclips,
)

import config as cfg
from config import AUDIO_DIR, FPS, FULL_VIDEOS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from utils import log_info, clean_title, split_into_sentences
from video_maker import _subtitle_overlay, _music_track


def _chapter_pieces(text: str):
    """Split a chapter into sentences, weighted by length (for subtitle timing)."""
    sentences = split_into_sentences(text)
    if not sentences:
        return []
    pad = 1.3  # extra weight per sentence so short lines don't flash by too fast
    total = sum(len(s) + pad for s in sentences)
    return [(s, (len(s) + pad) / total) for s in sentences]


def _rolling_subtitles(story: dict, total_narr_dur: float, size) -> list:
    """Build subtitle overlay clips across the whole timeline, sentence-paced."""
    all_weight = sum(len(ch["narration"]) + 2 for ch in story["chapters"])
    clips = []
    cursor = 0.0
    for ch in story["chapters"]:
        ch_frac = (len(ch["narration"]) + 2) / all_weight
        ch_dur = total_narr_dur * ch_frac
        for sent, frac in _chapter_pieces(ch["narration"]):
            d = ch_dur * frac
            sub = _subtitle_overlay(sent, d, size)
            if sub is None:
                continue
            sub = sub.set_start(cursor).set_duration(d)
            clips.append(sub)
            cursor += d
    return clips


def build_long_video(story: dict, image_path: Path, title: str = "") -> Path:
    """story['chapters'] with narrations; ONE image; ~15 min horizontal output."""
    ttl = title or clean_title(story["title"])
    video_size = (cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT)

    # ---- narration audio: chapter mp3s back-to-back ----
    ttl_clean = clean_title(story["title"])
    all_audio = []
    total_dur = 0.0
    for ch in story["chapters"]:
        mp3 = AUDIO_DIR / f"{ttl_clean}_long_ch{ch['id']:02d}.mp3"
        a = AudioFileClip(str(mp3))
        all_audio.append(a)
        total_dur += a.duration + 0.25
    narration = concatenate_audioclips([a for a in all_audio])
    log_info(f"Long narration duration: {narration.duration:.1f}s (~{narration.duration/60:.1f} min)")

    # ---- base image: Ken Burns over the FULL video ----
    # Pre-render the image once at max zoom, then slide a window over it per
    # frame (MoviePy 1.0.3's crop fx can't take callable positions).
    from PIL import Image as PILImage

    w, h = VIDEO_WIDTH, VIDEO_HEIGHT
    pil = PILImage.open(str(image_path)).convert("RGB")
    max_zoom = 1.25
    big_w, big_h = int(w * max_zoom), int(h * max_zoom + int(h * 0.3))
    scale = max(big_w / pil.width, big_h / pil.height)
    big_w, big_h = int(pil.width * scale), int(pil.height * scale)
    big_w = max(big_w, w); big_h = max(big_h, h)
    arr = np.array(pil.resize((big_w, big_h), PILImage.LANCZOS))
    max_dx = big_w - w
    max_dy = big_h - h
    x1 = max_dx // 2

    def frame_at(t):
        prog = t / max(narration.duration, 0.001)
        y = int(max_dy * (0.5 - 0.5 * math.cos(math.pi * prog)))
        return arr[y:y + h, x1:x1 + w]

    base = VideoClip(frame_at, duration=narration.duration)

    # ---- rolling subtitles aligned to narration ----
    subs = _rolling_subtitles(story, narration.duration, video_size)
    log_info(f"Subtitle overlays: {len(subs)}")

    final = CompositeVideoClip([base] + subs, size=video_size).set_audio(narration)

    music = _music_track(final.duration)
    if music is not None:
        from moviepy.audio.fx import audio_fadein
        final.audio = CompositeAudioClip([
            final.audio.volumex(cfg.NARRATION_VOLUME),
            music.fx(audio_fadein, 1.0),
        ])

    out_path = FULL_VIDEOS_DIR / f"{ttl}_long_full.mp4"
    final.write_videofile(
        str(out_path), fps=FPS, codec="libx264", audio_codec="aac",
        preset="fast", threads=2, logger=None,
    )
    log_info(f"Long video written: {out_path} ({final.duration/60:.1f} min)")
    return out_path


if __name__ == "__main__":
    import sys
    from utils import load_json

    sp = Path(sys.argv[1]).resolve()
    img = Path(sys.argv[2]).resolve()
    story = load_json(sp)
    out = build_long_video(story, img)
    print(out)