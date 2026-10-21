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

def supabase_insert_video(record: dict):
    """
    Saves video details to Supabase all_videos_db table.
    Note: file_hash is handled separately in MongoDB.
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
