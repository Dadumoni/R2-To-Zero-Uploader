import hashlib
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from config import MONGO_URI, MONGO_DB_NAME
from utils.logger import log

_mongo_client = None
_hashes_col = None

def get_mongo_collection():
    global _mongo_client, _hashes_col
    if _hashes_col is None:
        try:
            _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            db = _mongo_client[MONGO_DB_NAME]
            _hashes_col = db["video_hashes"]
            # Ensure indexes on hash and size
            _hashes_col.create_index([("file_hash", ASCENDING)], unique=True, background=True)
            _hashes_col.create_index([("file_size", ASCENDING)], background=True)
        except Exception as e:
            log(f"[MongoDB Error/Notice] {e}")
            _hashes_col = None
    return _hashes_col

def calculate_file_hash(file_path: Path) -> str:
    """
    Computes SHA-256 hash of the full file contents.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def mongo_check_duplicate(file_hash: str, file_size: int = None, duration: float = None) -> tuple[bool, str]:
    """
    Checks MongoDB for duplicate video:
    1. Exact SHA-256 hash match.
    2. Exact byte size + video duration match (tolerance 0.1s).
    """
    col = get_mongo_collection()
    if col is None:
        return False, ""

    try:
        # Layer 1: SHA-256 Hash Check
        if file_hash:
            doc = col.find_one({"file_hash": file_hash})
            if doc:
                return True, f"SHA-256 hash matched in MongoDB with slug '{doc.get('slug')}' ({doc.get('file_name')})"

        # Layer 2: File Size & Duration Check
        if file_size and file_size > 0 and duration and duration > 0:
            cursor = col.find({"file_size": file_size})
            for doc in cursor:
                doc_dur = doc.get("duration")
                if doc_dur is not None and abs(float(doc_dur) - float(duration)) < 0.1:
                    return True, f"File size ({file_size} B) & duration ({duration:.2f}s) matched in MongoDB with slug '{doc.get('slug')}' ({doc.get('file_name')})"

    except Exception as e:
        log(f"[MongoDB Duplicate Check Error] {e}")

    return False, ""

def mongo_save_video_hash(file_hash: str, slug: str, file_name: str, file_size: int, duration: float):
    """
    Saves the file hash and metadata to MongoDB for future duplicate tracking.
    """
    col = get_mongo_collection()
    if col is None:
        return

    try:
        col.update_one(
            {"file_hash": file_hash},
            {
                "$set": {
                    "file_hash": file_hash,
                    "slug": slug,
                    "file_name": file_name,
                    "file_size": file_size,
                    "duration": duration,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        log(f"[MongoDB] File hash and metadata saved for slug: {slug}")
    except Exception as e:
        log(f"[MongoDB Save Error] {e}")
