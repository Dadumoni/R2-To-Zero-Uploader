import gc
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

from utils.logger import log
from utils.media import make_title_and_filename, generate_smart_thumbnail, get_video_duration
from db.mongo import calculate_file_hash, mongo_check_duplicate, mongo_save_video_hash
from db.supabase_db import (
    supabase_get_next_slug,
    supabase_insert_video,
)
from storage.r2 import (
    download_from_r2,
    delete_from_r2,
    move_to_duplicate_folder,
    move_to_uploaded_folder,
    upload_thumb_to_r2,
)
from uploaders import upload_anonmp4_with_retry, upload_abyss, upload_zerostorage

def process_video(s3, video: dict, temp_dir: Path, processed_titles: set) -> bool:
    key       = video["key"]
    orig_ext  = Path(key).suffix.lower()
    orig_name = Path(key).name

    log("")
    log("=" * 65)
    log(f"PROCESSING : {orig_name}")
    log(f"R2 KEY     : {key}")
    log("=" * 65)

    # Generate 12-15 char random slug with letters, digits, and underscore (_)
    slug = supabase_get_next_slug()
    log(f"Assigned Slug: {slug}")

    # Video rename: Title has NO extension, while filename preserves original extension
    title, new_filename = make_title_and_filename(orig_ext)
    local_file = temp_dir / new_filename
    log(f"Assigned Title: {title}")
    log(f"Local Filename: {new_filename}")

    try:
        # Step 1: Download from R2
        download_from_r2(s3, key, local_file)

        # Step 2: Compute file metadata and SHA-256 hash
        file_hash = calculate_file_hash(local_file)
        file_size = local_file.stat().st_size
        duration = get_video_duration(local_file)

        log(f"File Hash: {file_hash}")
        log(f"File Size: {file_size / 1024 / 1024:.2f} MB, Duration: {duration:.2f}s")

        # Step 3: Tagda Duplicate Check using MongoDB (SHA-256 Hash + Size & Duration)
        is_dup, reason = mongo_check_duplicate(file_hash, file_size, duration)

        if is_dup:
            log(f"⚠ [DUPLICATE DETECTED] {reason}")
            log("Moving original file to 'Duplickte files/' folder in R2 and skipping upload.")
            move_to_duplicate_folder(s3, key)
            if local_file.exists():
                local_file.unlink()
            gc.collect()
            return True

        # Step 4: Generate Smart Composite Thumbnail based on Aspect Ratio
        log("[Thumbnail] Generating aspect-ratio based composite thumbnail...")
        thumb_path = generate_smart_thumbnail(local_file, slug, temp_dir)
        thumb_url = None
        if thumb_path and thumb_path.exists():
            thumb_url = upload_thumb_to_r2(thumb_path, slug)
            thumb_path.unlink()
            log(f"✔ Thumbnail Uploaded: {thumb_url}")
        gc.collect()

        # Step 5: Upload to Platforms (Untouched upload functions)
        # Launch lightweight Chromium ON-DEMAND only for AnonMP4 and close immediately to save 400MB RAM!
        log("[AnonMP4] Launching lightweight browser on-demand...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                    "--single-process",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--mute-audio",
                    "--no-first-run",
                    "--hide-scrollbars",
                ]
            )
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                anon_url = upload_anonmp4_with_retry(page, local_file)
            finally:
                context.close()
                browser.close()
        log(f"✔ AnonMP4: {anon_url}")
        gc.collect()

        log("[Abyss] Starting upload...")
        abyss_url = upload_abyss(local_file)
        log(f"✔ Abyss: {abyss_url}")
        gc.collect()

        log("[ZeroStorage] Starting upload...")
        zs_embed, zs_video = upload_zerostorage(local_file)
        log(f"✔ ZS Video: {zs_video}")
        gc.collect()

        # Step 6: Save record in Supabase all_videos_db (including file_hash, file_size, duration)
        record = {
            "slug":        slug,
            "title":       title,
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

        # Step 7: Save file hash and metadata in MongoDB for future deduplication
        mongo_save_video_hash(file_hash, slug, new_filename, file_size, duration)

        # Step 8: Cleanup local file & move original in R2 to 'uploaded-files/' folder (NO DELETION)
        if local_file.exists():
            local_file.unlink()

        move_to_uploaded_folder(s3, key)
        gc.collect()
        log("✔ COMPLETED AND MOVED TO 'uploaded-files/' SUCCESSFULLY")
        return True

    except Exception as e:
        log(f"✖ FAILED: {e}\n{traceback.format_exc()}")
        log(f"⚠ Video '{orig_name}' remains in watch folder for re-upload.")
        if local_file.exists():
            local_file.unlink()
        gc.collect()
        return False
