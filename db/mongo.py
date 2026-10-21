import hashlib
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME
from utils.logger import log

_mongo_client = None
_hashes_col = None

def get_mongo_collection():
    global _mongo_client, _hashes_col
    if _hashes_col is None:
        try:
            _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            db = _mongo_client[MONGO_DB_NAME]
            _hashes_col = db["video_hashes"]
        except Exception as e:
            log(f"[MongoDB Notice] MongoDB not available or skipped: {e}")
            _hashes_col = None
    return _hashes_col

def calculate_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def is_duplicate_hash(file_hash: str) -> bool:
    try:
        col = get_mongo_collection()
        if col is not None:
            return col.find_one({"file_hash": file_hash}) is not None
    except Exception:
        pass
    return False

def save_file_hash(file_hash: str, slug: str, file_name: str):
    try:
        col = get_mongo_collection()
        if col is not None:
            col.insert_one({
                "file_hash": file_hash,
                "slug": slug,
                "file_name": file_name,
                "created_at": datetime.utcnow()
            })
    except Exception:
        pass
