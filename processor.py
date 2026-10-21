from pathlib import Path
from utils.logger import log
from utils.media import make_rename, generate_smart_thumbnail, get_video_duration
from db.mongo import calculate_file_hash, is_duplicate_hash, save_file_hash
from db.supabase_db import (
    supabase_get_next_slug,
    supabase_check_duplicate,
    supabase_insert_video,
)
from storage.r2 import (
    download_from_r2,
    delete_from_r2,
    move_to_duplicate_folder,
    upload_thumb_to_r2,
)
from uploaders import upload_anonmp4_with_retry, upload_abyss, upload_zerostorage

def process_video(s3, page, video: dict, temp_dir: Path, processed_titles: set) -> bool:
    key       = video["key"]
    orig_ext  = Path(key).suffix.lower()
    orig_name = Path(key).name

    log("")
    log("=" * 65)
    log(f"PROCESSING : {orig_name}")
    log(f"R2 KEY     : {key}")
    log("=" * 65)

    slug = supabase_get_next_slug()
    # Video rename before uploading (using original extension)
    new_name = make_rename(orig_ext)
    local_file = temp_dir / new_name

    try:
        # Step 1: Download from R2
        download_from_r2(s3, key, local_file)

        # Step 2: Compute file metadata and SHA-256 hash
        file_hash = calculate_file_hash(local_file)
        file_size = local_file.stat().st_size
        duration = get_video_duration(local_file)

        log(f"File Hash: {file_hash}")
        log(f"File Size: {file_size / 1024 / 1024:.2f} MB, Duration: {duration:.2f}s")

        # Step 3: Tagda Duplicate Check (Supabase + MongoDB)
        is_dup, reason = supabase_check_duplicate(file_hash, file_size, duration)
        if not is_dup and is_duplicate_hash(file_hash):
            is_dup = True
            reason = "Matched in local MongoDB cache"

        if is_dup:
            log(f"⚠ [DUPLICATE DETECTED] {reason}")
            log("Moving original file to 'Duplickte files/' folder in R2 and skipping upload.")
            move_to_duplicate_folder(s3, key)
            if local_file.exists():
                local_file.unlink()
            return True

        # Step 4: Generate Smart Composite Thumbnail based on Aspect Ratio
        log("[Thumbnail] Generating aspect-ratio based composite thumbnail...")
        thumb_path = generate_smart_thumbnail(local_file, slug, temp_dir)
        thumb_url = None
        if thumb_path and thumb_path.exists():
            thumb_url = upload_thumb_to_r2(s3, thumb_path, slug)
            thumb_path.unlink()
            log(f"✔ Thumbnail Uploaded: {thumb_url}")

        # Step 5: Upload to Platforms (Untouched upload functions)
        log("[AnonMP4] Starting upload...")
        anon_url = upload_anonmp4_with_retry(page, local_file)
        log(f"✔ AnonMP4: {anon_url}")

        log("[Abyss] Starting upload...")
        abyss_url = upload_abyss(local_file)
        log(f"✔ Abyss: {abyss_url}")

        log("[ZeroStorage] Starting upload...")
        zs_embed, zs_video = upload_zerostorage(local_file)
        log(f"✔ ZS Video: {zs_video}")

        # Step 6: Save record in Supabase all_videos_db
        record = {
            "slug":        slug,
            "title":       new_name,
            "thumbnail":   thumb_url,
            "video_link":  zs_video,
            "zerostorage": zs_embed,
            "abyss":       abyss_url,
            "anonmp4":     anon_url,
            "file_hash":   file_hash,
            "file_size":   file_size,
            "duration":    duration,
        }
        supabase_insert_video(record)
        save_file_hash(file_hash, slug, new_name)

        # Step 7: Cleanup local file & remove original from R2 watch folder
        if local_file.exists():
            local_file.unlink()

        delete_from_r2(s3, key)
        log("✔ COMPLETED SUCCESSFULLY")
        return True

    except Exception as e:
        log(f"✖ FAILED: {e}")
        if local_file.exists():
            local_file.unlink()
        return False
