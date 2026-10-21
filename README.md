# R2 To Zero Uploader

Automated cloud video processing pipeline designed for 24/7 background operation and deployment on **Railway / Docker**.

---

## ⚡ Features

1. **R2 Watch & Auto Download**: Monitors Cloudflare R2 bucket watch folder for incoming videos.
2. **Robust Multi-Layer Deduplication**:
   - SHA-256 full file hash calculation.
   - Secondary fingerprinting (file size & duration tolerance).
   - If a duplicate video is found, it is moved automatically to the `Duplickte files/` folder in R2 and skipped.
3. **Smart Aspect-Ratio Thumbnails (16:9 1920x1080)**:
   - **9:16 (Vertical/Portrait/Shorts)**: Splits video into 3 equal parts, extracts frames, and composites into a 3-panel 16:9 thumbnail with dark dividers.
   - **16:9 (Horizontal/Landscape)**: Splits video into 4 parts and composites into a 2x2 grid thumbnail with divider cross.
   - **Other (4:3, 3:4, etc.)**: Splits video into 6 parts and composites into a 3x2 grid with blurred background cards and borders.
4. **Platform Uploaders (Zero-Memory Streamed)**:
   - **ZeroStorage**: 2MB chunked upload with UUID session tracking.
   - **Abyss**: Streamed multipart upload (prevents memory OOM issues).
   - **AnonMP4**: Headless Chromium Playwright automation with link retrieval.
5. **Supabase Integration**:
   - Stores metadata in `all_videos_db` (`slug`, `title`, `thumbnail`, `video_link`, `zerostorage`, `abyss`, `anonmp4`, `file_hash`, `file_size`, `duration`).
   - Automatically increments unique slugs (`vid000000000001`, ...).
6. **Railway Ready**: Includes Dockerfile with `ffmpeg`, Playwright Chromium, and Flask health server on port `$PORT`.

---

## 🛠️ Environment Variables (.env)

Configure the following variables in Railway or local `.env`:

```env
# Cloudflare R2
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
R2_BUCKET=your_bucket_name
R2_PUBLIC_URL=https://pub-xxxxxx.r2.dev
R2_WATCH_FOLDER=uploads/
R2_DUPLICATE_FOLDER=Duplickte files/

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_or_anon_key

# ZeroStorage
ZEROSTORAGE_API_KEY=your_zerostorage_api_key

# Optional
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=video_bot_db
PORT=8080
```

---

## 🚀 Railway Deployment

1. Connect your GitHub repository `Dadumoni/R2-To-Zero-Uploader` in [Railway](https://railway.app/).
2. Add your environment variables in the Railway dashboard under **Variables**.
3. Railway will automatically detect the `Dockerfile` and build:
   - Python 3.10 environment
   - FFmpeg & Playwright Chromium
   - Health check server bound to `$PORT`
