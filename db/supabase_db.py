import random
import string
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from utils.logger import log

_supabase_client: Client = None

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

def supabase_init_table():
    client = get_supabase_client()
    try:
        res = client.table("all_videos_db").select("id").limit(1).execute()
        log("Supabase table 'all_videos_db' connected and ready.")
    except Exception as e:
        log(f"Warning connecting to Supabase table 'all_videos_db': {e}")

def generate_random_slug(length: int = None) -> str:
    """
    Generates a 12-15 character random slug containing letters (a-z, A-Z), numbers (0-9), and underscore (_).
    Example: hjb8SNrKg_s8enRo
    """
    if length is None:
        length = random.randint(12, 15)
    charset = string.ascii_letters + string.digits + "_"
    return "".join(random.choices(charset, k=length))

def supabase_get_next_slug() -> str:
    """
    Generates a unique 12-15 character random slug and ensures no collision in Supabase.
    """
    client = get_supabase_client()
    for _ in range(10):
        slug = generate_random_slug()
        try:
            res = client.table("all_videos_db").select("id").eq("slug", slug).limit(1).execute()
            if not res.data:
                return slug
        except Exception:
            return slug
    return generate_random_slug(15)

def supabase_check_duplicate(file_hash: str, file_size: int = None, duration: float = None) -> tuple[bool, str]:
    """
    Checks Supabase database for duplicates:
    1. Exact SHA-256 file_hash check.
    2. File size and duration match (within 0.15s tolerance).
    """
    client = get_supabase_client()
    try:
        # Layer 1: Check SHA256 Hash
        if file_hash:
            res_hash = client.table("all_videos_db").select("slug, title, file_hash").eq("file_hash", file_hash).limit(1).execute()
            if res_hash.data and len(res_hash.data) > 0:
                match = res_hash.data[0]
                return True, f"SHA-256 hash matched in Supabase with slug '{match.get('slug')}' ({match.get('title')})"

        # Layer 2: Check matching File Size & Duration (within 0.15s tolerance)
        if file_size and file_size > 0 and duration and duration > 0:
            res_size = client.table("all_videos_db").select("slug, title, file_size, duration").eq("file_size", file_size).execute()
            if res_size.data:
                for row in res_size.data:
                    row_dur = row.get("duration")
                    if row_dur is not None and abs(float(row_dur) - float(duration)) < 0.15:
                        return True, f"File size ({file_size} B) & duration ({duration:.2f}s) matched in Supabase with slug '{row.get('slug')}' ({row.get('title')})"

    except Exception as e:
        log(f"[Supabase Duplicate Check Warning] {e}")

    return False, ""

def supabase_insert_video(record: dict):
    """
    Saves video details to Supabase all_videos_db table, including file_hash, file_size, and duration.
    """
    client = get_supabase_client()
    payload = {
        "slug":        record.get("slug"),
        "title":       record.get("title"),
        "thumbnail":   record.get("thumbnail"),
        "video_link":  record.get("video_link"),
        "zerostorage": record.get("zerostorage"),
        "abyss":       record.get("abyss"),
        "anonmp4":     record.get("anonmp4"),
        "file_hash":   record.get("file_hash"),
        "file_size":   record.get("file_size"),
        "duration":    record.get("duration"),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    
    res = client.table("all_videos_db").insert(payload).execute()
    log(f"Supabase record saved successfully for slug: {record.get('slug')}")
    return res

def supabase_get_processed_titles() -> set:
    client = get_supabase_client()
    try:
        res = client.table("all_videos_db").select("title").execute()
        rows = res.data or []
        return {row["title"] for row in rows if row.get("title")}
    except Exception as e:
        log(f"Warning fetching processed titles: {e}")
        return set()
