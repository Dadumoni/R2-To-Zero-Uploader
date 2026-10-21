import os
from dotenv import load_dotenv

load_dotenv()

# Cloudflare R2
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")
R2_WATCH_FOLDER = os.getenv("R2_WATCH_FOLDER", "uploads/")
R2_DUPLICATE_FOLDER = os.getenv("R2_DUPLICATE_FOLDER", "Duplickte files/")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# MongoDB (Optional Secondary Cache)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "video_bot_db")

# Uploaders
ZEROSTORAGE_API_KEY = os.getenv("ZEROSTORAGE_API_KEY")
ANONMP4_URL = "https://anonmp4.to"
ABYSS_UPLOAD_URL = "http://up.hydrax.net/9e805aa56a78e2abd1be605e7af7b3cb"

# App Settings
MAX_RETRIES = 3
UPLOAD_TIMEOUT = 30 * 60   # 30 min
WATCH_INTERVAL = 30        # seconds between polls when idle
UPLOAD_CHUNK_SIZE = 2 * 1024 * 1024   # 2 MB for ZeroStorage
PORT = int(os.getenv("PORT", 8080))

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
