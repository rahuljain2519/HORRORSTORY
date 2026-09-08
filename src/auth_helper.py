"""One-time OAuth setup: get a YouTube refresh token.

Run this ONCE on a machine with a browser:
    python src/auth_helper.py

It prints a Google sign-in URL. IMPORTANT:
  - Open the URL in an INCOGNITO window signed in ONLY as the account that
    owns your YouTube channel (the one listed as a Test user).
  - Approve the scopes -> you get redirected to a localhost page.
  - The script captures the code automatically and prints the refresh token.
"""
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import InstalledAppFlow

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"


def _build_installed_app_client():
    return {
        "installed": {
            "client_id": config.YOUTUBE_CLIENT_ID,
            "client_secret": config.YOUTUBE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [REDIRECT_URI, "http://localhost"],
        }
    }


def _make_server(flow):
    code_holder = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            code = qs.get("code", [None])[0]
            if code:
                code_holder["code"] = code
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<h3>Authorization complete!</h3>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No code received.")

        def log_message(self, *args):
            pass

    return code_holder, HTTPServer(("localhost", REDIRECT_PORT), Handler)


def main():
    if not config.YOUTUBE_CLIENT_ID or not config.YOUTUBE_CLIENT_SECRET:
        print(
            "\n[!] Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET first.\n"
            "    console.cloud.google.com -> APIs & Services -> Credentials\n"
            "    -> OAuth client -> Desktop app -> copy Client ID / Secret.\n"
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(
        _build_installed_app_client(), scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    authorization_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )

    code_holder, server = _make_server(flow)

    print("\n=================== STEP 1: LOG IN ===================")
    print("A browser window is opening with the Google sign-in URL.")
    print()
    print("IMPORTANT - you MUST approve with the correct account:")
    print("   -> sign in as the account that owns your YouTube channel")
    print("   -> it MUST be the account you added as a TEST USER")
    print("   -> if the wrong account is shown, use an INCOGNITO window")
    print("      and log in with the channel account only")
    webbrowser.open(authorization_url)
    print()
    print("If the wrong account opens, copy this URL into an incognito\n"
          "window and log in with the correct account:")
    print()
    print("    " + authorization_url)
    print()
    print("======================================================")

    server.handle_request()  # blocks until callback (or timeout)*
    server.server_close()

    code = code_holder.get("code")
    if not code:
        print("\n[!] No authorization code received. Make sure you approved")
        print("    the consent screen and the redirect reached localhost:8080.")
        sys.exit(1)

    flow.fetch_token(code=code)
    creds = flow.credentials

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