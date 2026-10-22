# R2 To Zero Uploader

Automated cloud video processing pipeline designed for 24/7 background operation and deployment on **Koyeb / Docker**.

---

## ⚡ Features

1. **R2 Watch & Auto Download**: Monitors Cloudflare R2 bucket watch folder for incoming videos.
2. **Robust Multi-Layer Deduplication**:
   - SHA-256 full file hash calculation.
   - Secondary fingerprinting (file size & duration tolerance) via MongoDB.
   - If a duplicate video is found, it is moved automatically to the `Duplickte files/` folder in R2 and skipped.
3. **Smart Aspect-Ratio Thumbnails with WebP Compression (16:9 1920x1080)**:
   - **9:16 (Vertical/Portrait/Shorts)**: Splits video into 3 equal parts, extracts frames, and composites into a 3-panel 16:9 thumbnail with dark dividers.
   - **16:9 (Horizontal/Landscape)**: Splits video into 4 parts and composites into a 2x2 grid thumbnail with divider cross.
   - **Other (4:3, 3:4, etc.)**: Splits video into 6 parts and composites into a 3x2 grid with blurred background cards and borders.
   - **Ultra-Compact WebP Compression**: Output is compressed to `.webp` format (quality 82, method 6), reducing thumbnail size to ~50-150 KB.
4. **Dedicated Thumbnail R2 Account**:
   - Supports uploading thumbnails to a **separate Cloudflare R2 account / bucket**.
   - Uploads to folder `new-thumbnail/` (e.g. `new-thumbnail/{slug}_thumb.webp`).
5. **Platform Uploaders (Zero-Memory Streamed)**:
   - **ZeroStorage**: 2MB chunked upload with UUID session tracking.
   - **Abyss**: Streamed multipart upload (prevents memory OOM issues).
   - **AnonMP4**: Headless Chromium Playwright automation with link retrieval.
6. **Supabase Integration**:
   - Stores metadata in `all_videos_db` (`slug`, `title`, `thumbnail`, `video_link`, `zerostorage`, `abyss`, `anonmp4`).
   - Automatically generates random 12-15 character unique alphanumeric slugs (e.g. `hjb8SNrKg_s8enRo`).
7. **Auto-Ping Keep-Alive**: Background thread pings `APP_URL/health` every 10 minutes to prevent Koyeb containers from idling or sleeping.
8. **Koyeb Ready**: Includes Debian 12 Bookworm Dockerfile with FFmpeg, Playwright Chromium, and Flask health server on port `8000`.

---

## 🛠️ Environment Variables (.env)

Configure the following variables in Koyeb or local `.env`:

```env
# Cloudflare R2 - Main Video Bucket (Watching uploads & moving duplicates)
R2_ENDPOINT=https://<main-account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_main_r2_access_key
R2_SECRET_KEY=your_main_r2_secret_key
R2_BUCKET=your_main_video_bucket
R2_PUBLIC_URL=https://pub-xxxxxx.r2.dev
R2_WATCH_FOLDER=uploads/
R2_DUPLICATE_FOLDER=Duplickte files/

# Cloudflare R2 - Separate Dedicated Thumbnail Account & Bucket
THUMB_R2_ENDPOINT=https://<thumb-account-id>.r2.cloudflarestorage.com
THUMB_R2_ACCESS_KEY=your_thumb_r2_access_key
THUMB_R2_SECRET_KEY=your_thumb_r2_secret_key
THUMB_R2_BUCKET=your_thumb_bucket_name
THUMB_R2_PUBLIC_URL=https://pub-xxxxxx.r2.dev
THUMB_FOLDER=new-thumbnail/

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_or_anon_key

# ZeroStorage
ZEROSTORAGE_API_KEY=your_zerostorage_api_key

# MongoDB
MONGO_URI=mongodb+srv://...
MONGO_DB_NAME=video_bot_db

# Koyeb & Auto-Ping Keep-Alive
PORT=8000
APP_URL=https://your-app-name.koyeb.app
PING_INTERVAL=600
```
