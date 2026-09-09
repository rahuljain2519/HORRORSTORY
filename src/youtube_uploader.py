"""Upload videos to YouTube via Data API v3 using a stored refresh token.

You must run auth_helper.py ONCE on a machine with a browser to obtain the
refresh token, then set it as an env var / GitHub secret.
"""
import re
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

import config
from utils import log_info, log_error, clean_title

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
SERVICE_NAME = "youtube"
API_VERSION = "v3"

CATEGORY_ENTERTAINMENT = "24"
CATEGORY_FILM_ANIMATION = "1"


def _clean_yt_title(text: str) -> str:
    """Remove special characters/emojis from upload titles (keep Hindi + Latin)."""
    cleaned = re.sub(r"[^\u0900-\u097F\uA8E0-\uA8FFA-Za-z0-9\s]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (cleaned or "Horror Story")[:100]


def _get_credentials():
    if not all([config.YOUTUBE_CLIENT_ID, config.YOUTUBE_CLIENT_SECRET,
                config.YOUTUBE_REFRESH_TOKEN]):
        raise RuntimeError(
            "Missing YouTube credentials. Run auth_helper.py once and set "
            "YOUTUBE_REFRESH_TOKEN (+ client id/secret)."
        )
    creds = Credentials(
        token="",
        refresh_token=config.YOUTUBE_REFRESH_TOKEN,
        client_id=config.YOUTUBE_CLIENT_ID,
        client_secret=config.YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    # Refresh eagerly: google-api-python-client can lazily send empty tokens
    # otherwise, producing "unregistered callers" 403 errors.
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    return creds


def get_youtube_service():
    return build(SERVICE_NAME, API_VERSION, credentials=_get_credentials())


def _upload(youtube, file_path: Path, title: str, description: str, tags: list,
            privacy: str, category_id: str) -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
            "defaultLanguage": "hi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(file_path), resumable=True, chunksize=4 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    uploaded = None
    while True:
        status, response = request.next_chunk()
        if response:
            log_info(f"Uploaded '{title}' -> videoId={response['id']}")
            uploaded = response["id"]
            break
    return uploaded


def upload_full(story: dict, video_path: Path, date_str: str, privacy: str = None):
    privacy = privacy or config.YOUTUBE_PRIVACY
    title = _clean_yt_title(f"{story['title']} डरावनी कहानी Horror Stories in Hindi")
    desc = (
        f"🕯️ {story['hook']}\n\n"
        f"🔥 भयानक कहानियाँ चैनल पर रोज़ नई हॉरर कहानी!\n\n"
        f"#horrorstory #hindihorror #bhayanakkahani #ghoststory #horrorvideos "
        f"#kahanian #paranormal #bhoot #halftimehorror"
    )
    tags = config.DEFAULT_TAGS + ["hindi horror full video", "300 seconds horror", "डरावनी कहानी"]
    youtube = get_youtube_service()
    return _upload(youtube, video_path, title, desc, tags, privacy, CATEGORY_ENTERTAINMENT)


def upload_short(story: dict, short_path: Path, variant: int, date_str: str,
                 privacy: str = None):
    privacy = privacy or config.YOUTUBE_PRIVACY
    title = _clean_yt_title(
        f"{story['title']} डरावनी सच्ची कहानी Part {variant} Shorts"
    )
    desc = (
        f"😱 {story['hook']}\n\n"
        f"भयानक कहानियाँ - रोज़ दो हॉरर shorts!\n"
        f"#shorts #horror #hindihorror #bhayanakkahani #ghoststory #shortsfeed"
    )
    tags = config.DEFAULT_TAGS + ["shorts", "horror kindigend", "viral horror"]
    youtube = get_youtube_service()
    return _upload(youtube, short_path, title, desc, tags, privacy, CATEGORY_ENTERTAINMENT)


def upload_long(story: dict, video_path: Path, date_str: str, privacy: str = None):
    """Upload a long-form (~15 min) story video."""
    privacy = privacy or config.YOUTUBE_PRIVACY
    title = _clean_yt_title(
        f"{story['title']} पूरी डरावनी कहानी Hindi Horror Story"
    )
    desc = (
        f"🕯️ {story['hook']}\n\n"
        f"🔥 {len(story.get('chapters', []))} अध्यायों वाली पूरी हिंदी हॉरर कहानी.\n\n"
        f"भयानक कहानियाँ चैनल पर रोज़ नई हॉरर कहानी!\n\n"
        f"#horrorstory #hindihorror #bhayanakkahani #ghoststory #horrorvideos "
        f"#kahanian #paranormal #bhoot #hindistor"
    )
    tags = config.DEFAULT_TAGS + ["full horror story", "15 minute horror story",
                                  "लंबी डरावनी कहानी", "पूरी कहानी"]
    youtube = get_youtube_service()
    return _upload(youtube, video_path, title, desc, tags, privacy, CATEGORY_ENTERTAINMENT)


def upload_all(story: dict, full_path: Path, short_paths: list[Path],
               date_str: str, privacy: str = None):
    ids = {"full": None, "shorts": []}
    try:
        ids["full"] = upload_full(story, full_path, date_str, privacy)
        for i, sp in enumerate(short_paths, start=1):
            ids["shorts"].append(upload_short(story, sp, i, date_str, privacy))
    except HttpError as e:
        log_error(f"YouTube error: {e}")
        raise
    return ids


if __name__ == "__main__":
    import sys

    story_path = Path(sys.argv[1])
    from utils import load_json
    story = load_json(story_path)
    ttl = clean_title(story["title"])
    full = Path(sys.argv[2]) if len(sys.argv) > 2 else list(config.FULL_VIDEOS_DIR.glob(f"{ttl}_full.mp4"))[0]
    shorts = sorted(config.SHORTS_DIR.glob(f"{ttl}_short*.mp4"))
    ids = upload_all(story, full, shorts, "2026-01-01")
    print(ids)