"""Assemble a 15-minute long story video from ONE image + long narration.

Single 16:9 image under the whole video with slow Ken Burns motion, rolling
subtitle text, chapter-by-chapter narration audio, and background music.

Targets ~15 min runtime for long-form YouTube uploads.
"""
import math
from pathlib import Path

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_audioclips,
)

import config as cfg
from config import AUDIO_DIR, FPS, FULL_VIDEOS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from utils import log_info, clean_title, split_into_sentences
from video_maker import _subtitle_overlay, _music_track


def _large_text_clips(text: str, size, frame_pad=2):
    """Split a long narration into sentence subtitle clips (rolling style).

    Returns subtitle overlays PROPORTIONAL to each sentence's length, so text
    keeps pace with the audio. Compensates for long scratch delays with padding.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []
    longest = max(len(s) for s in sentences)
    need_wrap = longest > 55  # anything much longer than a line gets padded wrap
    base_share = 1.0 if not need_wrap else 1.3

    total_chars = sum(len(s) + base_share for s in sentences)
    dur_per_char = 1.0  # fallback; real timing set by caller

    clips = []
    spent = 0.0
    for s in sentences:
        weight = len(s) + base_share
        frac = weight / total_chars
        clips.append((s, frac))
        spent += frac
    return clips


def _rolling_subtitles(story: dict, total_narr_dur: float, size) -> list:
    """Build [start, end, subtitle_image] timings across the whole timeline."""
    from PIL import Image
    import numpy as np

    img_subdur = []
    cursor = 0.0

    # chapters laid out back-to-back
    all_chars = sum(len(ch["narration"]) + 2 for ch in story["chapters"])
    for ch in story["chapters"]:
        text = ch["narration"]
        ch_frac = (len(text) + 2) / all_chars
        ch_dur = total_narr_dur * ch_frac

        pieces = _large_text_clips(text, size)
        for sent, frac in pieces:
            d = ch_dur * frac
            sub = _subtitle_overlay(sent, d, size)
            if sub is None:
                continue
            sub = sub.set_start(cursor).set_duration(d)
            img_subdur.append(sub)
            cursor += d
    return img_subdur


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
    base = ImageClip(str(image_path))
    base = base.resize(height=max(cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT) * 1.2)
    base = base.resize(lambda t: 1.0 + 0.05 * (t / max(narration.duration, 0.001)))
    bw, bh = base.size
    tw, th = cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT
    bw = max(bw, tw)
    max_dx = bw - tw
    max_dy = max(bh - th, 0)
    x1 = max_dx // 2
    if max_dy > 0:
        def drift(t):
            return int(max_dy * (0.5 - 0.5 * math.cos(math.pi * t / narration.duration)))
        base = base.crop(x1=x1, y1=drift, x2=x1 + tw, y2=lambda t: drift(t) + th)
    else:
        base = base.crop(x1=x1, y1=0, x2=x1 + tw, y2=th)
    base = base.set_duration(narration.duration)

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