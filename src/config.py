"""Central configuration for the horror story agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

# MoviePy 1.0.3 uses PIL.Image.ANTIALIAS which Pillow 10+ removed.
# Patch it to LANCZOS so moviepy works with modern Pillow.
try:
    from PIL import Image
    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

load_dotenv()

# --- Paths ----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
BG_MUSIC_DIR = ASSETS_DIR / "bg_music"
FONTS_DIR = ASSETS_DIR / "fonts"
INTRO_OUTRO_DIR = ASSETS_DIR / "intro_outro"

OUTPUT_DIR = ROOT / "output"
STORIES_DIR = OUTPUT_DIR / "stories"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
FULL_VIDEOS_DIR = OUTPUT_DIR / "full_videos"
SHORTS_DIR = OUTPUT_DIR / "shorts"

for d in (STORIES_DIR, IMAGES_DIR, AUDIO_DIR, FULL_VIDEOS_DIR, SHORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- YouTube API -----------------------------------------------------------
def _env(name, default=""):
    """Env value with empty-string treated as the default."""
    return (os.getenv(name) or default).strip()


YOUTUBE_CLIENT_ID = _env("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = _env("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = _env("YOUTUBE_REFRESH_TOKEN")

# --- Story generation -------------------------------------------------------
STORY_API_MODE = _env("STORY_API_MODE", "ollama").lower()  # ollama | gemini | cloud
OLLAMA_HOST = _env("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "llama3.2")
# Free tier: get a key at https://aistudio.google.com/apikey  (Google AI Studio)
GOOGLE_AI_API_KEY = _env("GOOGLE_AI_API_KEY")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.0-flash")

# --- Image generation (Pollinations.ai - free) --------------------------------
POLLINATIONS_BASE = _env("POLLINATIONS_BASE", "https://image.pollinations.ai/prompt/")
# A "referrer" lets Pollinations rate-limit per-app instead of per-IP.
# Cloud IPs (GitHub runners) get throttled hard without it.
POLLINATIONS_REFERRER = _env("POLLINATIONS_REFERRER", "https://github.com/rahuljain2519/HORRORSTORY")

# --- Voice generation (edge-tts - free) ---------------------------------------
VOICE_NAME = _env("VOICE_NAME", "hi-IN-MadhurNeural")
VOICE_RATE = _env("VOICE_RATE", "+0%")   # e.g. -10% for slower spooky
VOICE_VOLUME = _env("VOICE_VOLUME", "+0%")

# --- Video params ---------------------------------------------------------------
ORIENTATION = _env("VIDEO_ORIENTATION", "vertical").lower()
if ORIENTATION == "horizontal":
    VIDEO_WIDTH, VIDEO_HEIGHT = 1920, 1080
else:  # vertical = shorts-first strategy
    VIDEO_WIDTH, VIDEO_HEIGHT = 1080, 1920

FPS = 30
IMAGE_DURATION = 5.0            # seconds per image
FADE_DURATION = 0.5
KENBURNS_MODE = "zoom"          # zoom | pan
FONT_CANDIDATES = [
    "assets/fonts/hindi.ttf",
    "C:/Windows/Fonts/Nirmala.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
]
BG_MUSIC_VOLUME = 0.15
NARRATION_VOLUME = 1.0

# --- Shorts / story structure ----------------------------------------------------
SHORTS_PER_STORY = 2            # how many shorts derived from one story
SHORT_DURATION_MAX = 60         # seconds (YouTube Shorts cap is 60s)
FULL_VIDEO_MAX_SECONDS = 300    # 5 min

# --- YouTube upload defaults ------------------------------------------------------
YOUTUBE_PRIVACY = _env("YOUTUBE_PRIVACY", "private")  # start private, then public
DEFAULT_TAGS = [
    "horror story",
    "hindi horror kahani",
    "bhayanak kahani",
    "ghost story",
    "paranormal stories",
    "horror videos",
    "kahaniyan",
    "goosebumps stories",
    "raw sound horror",
    "horror shorts",
]

# --- misc ----------------------------------------------------------------------------
HF_TORCH = True

def ensure_font():
    """Pick the first font file that exists, return path or None."""
    for f in FONT_CANDIDATES:
        p = Path(f)
        if p.exists():
            return str(p)
    return None