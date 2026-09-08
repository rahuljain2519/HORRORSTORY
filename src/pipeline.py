"""Daily pipeline: story -> images -> voice -> full video -> 2 shorts -> upload.

Run on GitHub Actions (STORY_API_MODE=cloud) or locally (STORY_API_MODE=ollama).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from utils import log_info, log_error, save_json, load_json, clean_title  # noqa: E402


def is_upload_configured() -> bool:
    return bool(config.YOUTUBE_CLIENT_ID and config.YOUTUBE_CLIENT_SECRET
                and config.YOUTUBE_REFRESH_TOKEN)


def run():
    log_info("===== HORROR STORY DAILY PIPELINE START =====")

    # 1) Story ---------------------------------------------------------------
    from story_generator import generate_story
    story, story_path = generate_story()
    log_info(f"Story ready: {story['title']} ({len(story['scenes'])} scenes)")

    # 2) Thumbnail / images ----------------------------------------------------
    from image_generator import generate_images
    images = generate_images(story, portrait=(config.VIDEO_HEIGHT > config.VIDEO_WIDTH))
    log_info(f"Images generated: {len(images)}")

    # 3) Voice -----------------------------------------------------------------
    from voice_generator import run_generate_voice
    clips = run_generate_voice(story)
    log_info(f"Voice clips generated: {len(clips)}")

    # 4) Full video -------------------------------------------------------------
    from video_maker import build_full_video
    full_video = build_full_video(story, images, title=clean_title(story["title"]))
    log_info(f"Full video: {full_video}")

    # 5) Shorts (2 short films from the same story) --------------------------------
    from short_maker import make_shorts
    shorts = make_shorts(full_video, story)
    log_info(f"Shorts generated: {len(shorts)}")

    # 6) Upload ---------------------------------------------------------------------
    date_str = date.today().isoformat()
    if is_upload_configured():
        from youtube_uploader import upload_all
        try:
            ids = upload_all(story, full_video, shorts, date_str)
            log_info(f"Uploaded -> full:{ids['full']} shorts:{ids['shorts']}")
            manifest = {
                "date": date_str,
                "title": story["title"],
                "story_file": str(story_path),
                "full_video": str(full_video),
                "shorts": [str(s) for s in shorts],
                "youtube_ids": ids,
            }
            save_json(manifest, config.OUTPUT_DIR / f"manifest_{date_str}.json")
        except Exception as e:  # noqa: BLE001
            log_error(f"Upload failed (keep artifacts; retry manually): {e}")
    else:
        log_info("YouTube not configured -> SKIPPING upload (videos kept locally).")

    log_info("===== PIPELINE COMPLETE =====")
    return story_path


if __name__ == "__main__":
    run()