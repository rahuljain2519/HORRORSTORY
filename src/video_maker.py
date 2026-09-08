"""Assemble the full horror story video with MoviePy + FFmpeg.

Pipeline per scene:
  image -> Ken Burns clip (zoom/pan) lasting == narration clip duration
  subtitle text (Hindi) burned in on lower third (rendered via PIL)
  background music (looped, low volume) mixed under narration
  intro hook scene + end subscribe card
"""
import math
from pathlib import Path

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

import config as cfg
from config import AUDIO_DIR, FADE_DURATION, FPS, FULL_VIDEOS_DIR, IMAGE_DURATION
from utils import log_info, clean_title, find_devanagari_font


def _make_text_image(text: str, size, position="lower", font_scale=0.045):
    """Render Hindi subtitle to a transparent PNG via Pillow (no ImageMagick)."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = int(w * font_scale)

    custom_font = find_devanagari_font()
    if custom_font:
        try:
            font = ImageFont.truetype(custom_font, font_size)
        except Exception:  # noqa: BLE001
            font = None
    else:
        font = None
    if font is None:
        # Fallback: if no Devanagari font, skip text (avoid tofu boxes)
        return None

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    max_w = int(w * 0.88)
    if tw > max_w:
        # simple wrap on words
        words = text.split()
        lines, cur = [], ""
        for word in words:
            test = f"{cur} {word}".strip()
            tb = draw.textbbox((0, 0), test, font=font)
            if tb[2] - tb[0] <= max_w:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        text_render = "\n".join(lines)
        tb = draw.textbbox((0, 0), text_render, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
    else:
        text_render = text

    x = (w - tw) // 2
    y = int(h * 0.70) if position == "lower" else (h - th) // 2

    draw.text((x + 3, y + 3), text_render, font=font, fill=(0, 0, 0, 200))  # shadow
    draw.text((x, y), text_render, font=font, fill=(255, 255, 255, 255))
    return img


def _subtitle_overlay(text: str, duration: float, size):
    """Return a VideoClip with PIL subtitle or None."""
    img = _make_text_image(text, size)
    if img is None:
        return None
    import numpy as np
    from moviepy.editor import ImageClip as _IC
    return _IC(np.array(img)).set_duration(duration)


def _kenburns_clip(image_path: Path, duration: float, size):
    """Slow cinematic Ken Burns (zoom + drift) - deterministic."""
    clip = ImageClip(str(image_path))
    # resize so the *long* side covers the target, keeping aspect
    clip = clip.resize(height=max(size) * 1.15)
    # then slow zoom
    clip = clip.resize(lambda t: 1.0 + 0.08 * (t / max(duration, 0.001)))
    return _finalize_crop(clip, duration, size)


def _finalize_crop(clip, duration, size):
    """Crop a resized clip to exact target size, centered, with slow vertical drift."""
    tw, th = cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT
    clip = clip.resize(height=th)
    cw, ch = clip.size
    if cw < tw:
        clip = clip.resize(width=tw)
        cw, ch = clip.size
    max_x = cw - tw
    max_y = ch - th
    x1 = (max_x // 2) if max_x > 0 else 0
    y1 = 0
    if max_y > 0:
        # drift from top to bottom across the duration
        def y1f(t):
            prog = t / max(duration, 0.001)
            return int(max_y * (0.5 - 0.5 * math.cos(math.pi * prog)))
        clip = clip.crop(x1=x1, y1=y1f, x2=x1 + tw, y2=lambda t: y1f(t) + th)
    else:
        clip = clip.crop(x1=x1, y1=0, x2=x1 + tw, y2=th)
    return clip.set_duration(duration)


def _music_track(total_duration: float):
    """Loop up the first bg music file to length, at low volume."""
    mp3_files = sorted(cfg.BG_MUSIC_DIR.glob("*.mp3")) or sorted(cfg.BG_MUSIC_DIR.glob("*.wav"))
    if not mp3_files:
        return None
    music = AudioFileClip(str(mp3_files[0]))
    if music.duration < total_duration:
        repeats = int(math.ceil(total_duration / max(music.duration, 0.01)))
        blocks = [music] * repeats
        from moviepy.editor import concatenate_audioclips
        music = concatenate_audioclips(blocks).subclip(0, total_duration)
    else:
        music = music.subclip(0, total_duration)
    return music.volumex(cfg.BG_MUSIC_VOLUME)


def build_full_video(story: dict, images: list[Path], title: str = "") -> Path:
    """images[0]=cover, images[1:]=scene images in order. Narrations pre-generated."""
    ttl = title or clean_title(story["title"])
    video_size = (cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT)

    video_clips = []

    # ---- intro hook scene ----
    intro_audio = AudioFileClip(str(AUDIO_DIR / f"{ttl}_intro.mp3"))
    intro_len = intro_audio.duration + 0.4
    intro_base = _kenburns_clip(images[0], intro_len, video_size)
    sub = _subtitle_overlay(story["hook"], intro_len, video_size)
    intro_clip = CompositeVideoClip([intro_base, sub], size=video_size) if sub else intro_base
    intro_clip = intro_clip.set_audio(intro_audio)
    video_clips.append(intro_clip)

    # ---- main scenes ----
    for i, sc in enumerate(story["scenes"]):
        img = images[i + 1] if i + 1 < len(images) else images[-1]
        mp3 = AUDIO_DIR / f"{ttl}_scene{sc['id']:02d}.mp3"
        audio = AudioFileClip(str(mp3))
        seg_len = max(audio.duration + 0.4, IMAGE_DURATION)

        base = _kenburns_clip(img, seg_len, video_size)
        sub = _subtitle_overlay(sc["narration"], seg_len, video_size)
        seg = CompositeVideoClip([base, sub], size=video_size) if sub else base
        seg = seg.set_audio(audio)
        video_clips.append(seg)

    # ---- end card ----
    end_audio = AudioFileClip(str(AUDIO_DIR / f"{ttl}_intro.mp3"))
    end_len = min(8, end_audio.duration)
    end_audio = end_audio.subclip(0, end_len)
    end_base = _kenburns_clip(images[0], end_len, video_size)
    end_text = _subtitle_overlay("लाइक और सब्सक्राइब करें", end_len, video_size)
    end_card = CompositeVideoClip([end_base, end_text], size=video_size) if end_text else end_base
    end_card = end_card.set_audio(end_audio)
    video_clips.append(end_card)

    # ---- assemble & export ----
    final = concatenate_videoclips(video_clips, method="compose").fadeout(FADE_DURATION)
    music = _music_track(final.duration)
    if music is not None:
        from moviepy.audio.fx import audio_fadein
        final.audio = CompositeAudioClip([
            final.audio.volumex(cfg.NARRATION_VOLUME),
            music.fx(audio_fadein, 1.0),
        ])

    out_path = FULL_VIDEOS_DIR / f"{ttl}_full.mp4"
    final.write_videofile(
        str(out_path), fps=FPS, codec="libx264", audio_codec="aac",
        preset="medium", threads=2, logger=None,
    )
    log_info(f"Full video written: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    from utils import load_json

    sp = Path(sys.argv[1])
    story = load_json(sp)
    imgs = sorted(cfg.IMAGES_DIR.glob(f"{clean_title(story['title'])}_*.jpg"))
    out = build_full_video(story, imgs)
    print(out)