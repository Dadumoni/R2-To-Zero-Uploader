from pathlib import Path
import boto3
from botocore.config import Config
from config import (
    R2_ENDPOINT,
    R2_ACCESS_KEY,
    R2_SECRET_KEY,
    R2_BUCKET,
    R2_PUBLIC_URL,
    R2_WATCH_FOLDER,
    R2_DUPLICATE_FOLDER,
    THUMB_R2_ENDPOINT,
    THUMB_R2_ACCESS_KEY,
    THUMB_R2_SECRET_KEY,
    THUMB_R2_BUCKET,
    THUMB_R2_PUBLIC_URL,
    THUMB_FOLDER,
    VIDEO_EXTENSIONS,
    validate_config,
)
from utils.logger import log

_thumb_s3_client = None

def create_r2_client():
    validate_config()
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "adaptive"}),
    )

def get_thumb_r2_client():
    """
    Returns S3 client for dedicated Thumbnail R2 account / bucket.
    """
    global _thumb_s3_client
    if _thumb_s3_client is None:
        _thumb_s3_client = boto3.client(
            "s3",
            endpoint_url=THUMB_R2_ENDPOINT,
            aws_access_key_id=THUMB_R2_ACCESS_KEY,
            aws_secret_access_key=THUMB_R2_SECRET_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "adaptive"}),
        )
    return _thumb_s3_client

def list_videos(s3):
    prefix = R2_WATCH_FOLDER.strip()
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    videos = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            ext = Path(key).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                videos.append({"key": key, "size": obj["Size"]})
    return videos

def delete_from_r2(s3, key: str):
    log(f"Deleting original video from R2: {key}")
    s3.delete_object(Bucket=R2_BUCKET, Key=key)

def move_to_duplicate_folder(s3, key: str) -> str:
    """
    Moves a duplicate file from the watch folder to 'Duplickte files/' folder in R2.
    """
    dup_folder = R2_DUPLICATE_FOLDER.strip()
    if dup_folder and not dup_folder.endswith("/"):
        dup_folder += "/"

    file_name = Path(key).name
    target_key = f"{dup_folder}{file_name}"

    log(f"Moving duplicate in R2: '{key}' -> '{target_key}'")
    s3.copy_object(
        Bucket=R2_BUCKET,
        CopySource={"Bucket": R2_BUCKET, "Key": key},
        Key=target_key,
    )
    s3.delete_object(Bucket=R2_BUCKET, Key=key)
    log(f"Duplicate successfully moved to '{target_key}'.")
    return target_key

def download_from_r2(s3, key: str, destination: Path):
    log(f"Downloading: {key}")
    s3.download_file(R2_BUCKET, key, str(destination))
    if not destination.exists():
        raise RuntimeError("Download completed but file missing.")
    log(f"Downloaded: {destination.stat().st_size / 1024 / 1024:.2f} MB")

def upload_thumb_to_r2(thumb_path: Path, slug: str) -> str:
    """
    Uploads compressed thumbnail to the separate thumbnail R2 account inside 'new-thumbnail/' folder.
    """
    folder = THUMB_FOLDER.strip()
    if folder and not folder.endswith("/"):
        folder += "/"

    ext = thumb_path.suffix.lower() or ".webp"
    r2_key = f"{folder}{slug}_thumb{ext}"

    content_type = "image/webp" if ext == ".webp" else ("image/avif" if ext == ".avif" else "image/jpeg")

    thumb_s3 = get_thumb_r2_client()
    log(f"[Thumbnail] Uploading to dedicated R2 bucket '{THUMB_R2_BUCKET}' as '{r2_key}' (Content-Type: {content_type})...")

    thumb_s3.upload_file(
        str(thumb_path),
        THUMB_R2_BUCKET,
        r2_key,
        ExtraArgs={"ContentType": content_type},
    )

    if THUMB_R2_PUBLIC_URL:
        return f"{THUMB_R2_PUBLIC_URL}/{r2_key}"
    clean_endpoint = THUMB_R2_ENDPOINT.replace("https://", "").replace("http://", "").rstrip("/")
    return f"https://{THUMB_R2_BUCKET}.{clean_endpoint}/{r2_key}"
