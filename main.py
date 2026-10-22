import gc
import time
import tempfile
import threading
from pathlib import Path

from config import WATCH_INTERVAL, validate_config
from server.health import run_health_server
from storage.r2 import create_r2_client, list_videos
from db.supabase_db import supabase_init_table, supabase_get_processed_titles
from processor import process_video
from utils.logger import log

def main():
    # Start health check & keepalive auto-ping in background thread
    threading.Thread(target=run_health_server, daemon=True, name="HealthServer").start()

    validate_config()
    s3 = create_r2_client()
    supabase_init_table()

    temp_dir = Path(tempfile.mkdtemp(prefix="r2_backup_"))
    log("Lightweight watcher loop active (Zero background browser memory overhead).")

    while True:
        try:
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
                ok = process_video(s3, video, temp_dir, processed_titles)
                if ok:
                    already_done.add(video["key"])
                else:
                    # If any platform failed, ensure key is NOT marked done so it retries
                    already_done.discard(video["key"])
                gc.collect()

            main._processed_keys = already_done
            time.sleep(WATCH_INTERVAL)

        except Exception as e:
            log(f"Error in watcher loop: {e}")
            time.sleep(WATCH_INTERVAL)

if __name__ == "__main__":
    main()
