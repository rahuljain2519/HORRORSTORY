"""On-demand pipeline for a LONG (target ~15 min) single-image horror story.

Story -> 1 image (all characters) -> chapter narrations -> one 16:9 video -> upload.

Run manually (workflow_dispatch) so it does not disturb the daily shorts run.
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from utils import log_info, log_error, save_json, load_json, clean_title  # noqa: E402


def run_long():
    log_info("===== LONG HORROR STORY PIPELINE START =====")

    from long_story_generator import generate_long_story
    story, story_path = generate_long_story()
    log_info(f"Long story ready: {story['title']} ({len(story['chapters'])} chapters, "
             f"{sum(len(c['narration']) for c in story['chapters'])} chars)")

    # ---- ONE image with all characters ----
    from image_generator import ImageSpec, _download
    ttl = clean_title(story["title"])
    width, height = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
    img = _download(
        ImageSpec(prompt=story["cover_prompt"], filename=f"{ttl}_long_cover.jpg", seed=4242),
        width, height,
    )
    log_info(f"Single long-story image: {img}")

    # ---- chapter narrations ----
    from voice_generator import _synth, _estimate_duration

    async def gen_voice():
        paths = []
        for ch in story["chapters"]:
            p = config.AUDIO_DIR / f"{ttl}_long_ch{ch['id']:02d}.mp3"
            await _synth(ch["narration"], p)
            paths.append((ch, p, _estimate_duration(p, ch["narration"])))
            log_info(f"Chapter {ch['id']}: {p.name} ({paths[-1][2]:.1f}s)")
        return paths

    chapters_audio = asyncio.run(gen_voice())
    total_narr = sum(d for _, _, d in chapters_audio)
    log_info(f"Total narration: {total_narr:.0f}s (~{total_narr/60:.1f} min)")

    # ---- long video (16:9) ----
    from long_video_maker import build_long_video
    full_video = build_long_video(story, img, title=ttl)
    log_info(f"Long video: {full_video}")

    # ---- upload ----
    date_str = date.today().isoformat()
    if config.YOUTUBE_CLIENT_ID and config.YOUTUBE_CLIENT_SECRET and config.YOUTUBE_REFRESH_TOKEN:
        from youtube_uploader import upload_long
        try:
            vid = upload_long(story, full_video, date_str)
            log_info(f"Uploaded long video -> videoId={vid}")
            save_json({
                "date": date_str,
                "title": story["title"],
                "story_file": str(story_path),
                "long_video": str(full_video),
                "youtube_ids": {"long": vid},
                "mode": "long",
            }, config.OUTPUT_DIR / f"manifest_long_{date_str}.json")
        except Exception as e:  # noqa: BLE001
            log_error(f"Long upload failed (keep artifacts): {e}")
            raise
    else:
        log_info("YouTube not configured -> SKIPPING long upload.")

    log_info("===== LONG PIPELINE COMPLETE =====")
    return story_path


if __name__ == "__main__":
    run_long()