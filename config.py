import os
from dotenv import load_dotenv

load_dotenv()

# Cloudflare R2 - Main Video Account / Bucket
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")
R2_WATCH_FOLDER = os.getenv("R2_WATCH_FOLDER", "uploads/")
R2_DUPLICATE_FOLDER = os.getenv("R2_DUPLICATE_FOLDER", "Duplickte files/")

# Cloudflare R2 - Dedicated Thumbnail Account / Bucket
THUMB_R2_ENDPOINT = os.getenv("THUMB_R2_ENDPOINT") or R2_ENDPOINT
THUMB_R2_ACCESS_KEY = os.getenv("THUMB_R2_ACCESS_KEY") or R2_ACCESS_KEY
THUMB_R2_SECRET_KEY = os.getenv("THUMB_R2_SECRET_KEY") or R2_SECRET_KEY
THUMB_R2_BUCKET = os.getenv("THUMB_R2_BUCKET") or R2_BUCKET
THUMB_R2_PUBLIC_URL = os.getenv("THUMB_R2_PUBLIC_URL", "").rstrip("/") or R2_PUBLIC_URL
THUMB_FOLDER = os.getenv("THUMB_FOLDER", "new-thumbnail/").strip()

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "video_bot_db")

# Uploaders
ZEROSTORAGE_API_KEY = os.getenv("ZEROSTORAGE_API_KEY")
ANONMP4_URL = "https://anonmp4.to"
ABYSS_UPLOAD_URL = "http://up.hydrax.net/9e805aa56a78e2abd1be605e7af7b3cb"

# App & Server Settings (Koyeb uses PORT=8000 by default)
PORT = int(os.getenv("PORT", 8000))
MAX_RETRIES = 3
UPLOAD_TIMEOUT = 30 * 60   # 30 min
WATCH_INTERVAL = 30        # seconds between polls when idle
UPLOAD_CHUNK_SIZE = 2 * 1024 * 1024   # 2 MB for ZeroStorage

# Auto-Ping (Keep alive every 10 minutes)
APP_URL = os.getenv("APP_URL") or os.getenv("PING_URL") or os.getenv("KOYEB_PUBLIC_URL", "")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", 600))  # 600s = 10 minutes

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".flv", ".wmv", ".mpeg", ".mpg", ".m4v",
    ".ts", ".3gp", ".ogv", ".vob",
}

def validate_config():
    required = {
        "R2_ENDPOINT": R2_ENDPOINT,
        "R2_ACCESS_KEY": R2_ACCESS_KEY,
        "R2_SECRET_KEY": R2_SECRET_KEY,
        "R2_BUCKET": R2_BUCKET,
        "ZEROSTORAGE_API_KEY": ZEROSTORAGE_API_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(
            "Missing .env variables:\n" + "\n".join(f"  - {x}" for x in missing)
        )
