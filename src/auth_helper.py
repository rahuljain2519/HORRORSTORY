"""One-time OAuth setup: get a YouTube refresh token.

Run this ONCE on a machine with a browser:
    python src/auth_helper.py

It will print a URL -> open it, sign in with the channel's Google account,
approve scopes, paste the code back, and it writes the refresh token to
your console (and optionally to .env / GitHub secret guidance).
"""
import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _build_installed_app_client():
    """YouTube Data API v3 uses 'installed app' OAuth flow."""
    return {
        "installed": {
            "client_id": config.YOUTUBE_CLIENT_ID,
            "client_secret": config.YOUTUBE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }


def main():
    if not config.YOUTUBE_CLIENT_ID or not config.YOUTUBE_CLIENT_SECRET:
        print(
            "\n[!] Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET first.\n"
            "    console.cloud.google.com -> APIs & Services -> Credentials\n"
            "    -> OAuth client -> Desktop app -> copy Client ID / Secret.\n"
        )
        sys.exit(1)

    client_info = _build_installed_app_client()
    flow = InstalledAppFlow.from_client_config(client_info, scopes=SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", open_browser=True)

    print("\n================= YOUR REFRESH TOKEN =================")
    print(creds.refresh_token)
    print("=====================================================")
    print("""
Next steps:
  1) Add to local .env:
       YOUTUBE_REFRESH_TOKEN=<paste above>
  2) For GitHub Actions, add as a secret named YOUTUBE_REFRESH_TOKEN
     in your repo Settings -> Secrets and variables -> Actions.
  3) Also add YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET as secrets.
""")


if __name__ == "__main__":
    main()