import time
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

from config import WATCH_INTERVAL, validate_config
from server.health import run_health_server
from storage.r2 import create_r2_client, list_videos
from db.supabase_db import supabase_init_table, supabase_get_processed_titles
from processor import process_video

def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    validate_config()
    s3 = create_r2_client()
    supabase_init_table()

    temp_dir = Path(tempfile.mkdtemp(prefix="r2_backup_"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            while True:
                videos = list_videos(s3)
                if not videos:
                    time.sleep(WATCH_INTERVAL)
                    continue

                processed_titles = supabase_get_processed_titles()
                already_done = getattr(main, "_processed_keys", set())
                new_videos = [v for v in videos if v["key"] not in already_done]

                if not new_videos:
                    time.sleep(WATCH_INTERVAL)
                    continue

                for i, video in enumerate(new_videos, start=1):
                    ok = process_video(s3, page, video, temp_dir, processed_titles)
                    if ok:
                        already_done.add(video["key"])
                main._processed_keys = already_done
                time.sleep(WATCH_INTERVAL)

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
