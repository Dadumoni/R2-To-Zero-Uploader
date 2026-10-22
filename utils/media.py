import json
import math
import subprocess
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from utils.logger import log

CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080

def make_rename(ext: str) -> str:
    ts = datetime.now().strftime("%d%m%y%H%M%S")
    return f"TG-@atoz_links-VID-{ts}{ext}"

def get_video_info(video_path: Path) -> dict:
    """
    Extracts video width, height, duration and file size using ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-show_entries", "format=duration,size",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(res.stdout) if res.stdout else {}
        stream = data.get("streams", [{}])[0] if data.get("streams") else {}
        fmt = data.get("format", {})

        width = int(stream.get("width") or 1920)
        height = int(stream.get("height") or 1080)

        dur_str = stream.get("duration") or fmt.get("duration")
        duration = float(dur_str) if dur_str else 0.0

        size = int(fmt.get("size") or video_path.stat().st_size)
        aspect_ratio = width / height if height > 0 else (16.0 / 9.0)

        return {
            "width": width,
            "height": height,
            "duration": duration,
            "size": size,
            "aspect_ratio": aspect_ratio,
        }
    except Exception as e:
        log(f"Error reading video metadata via ffprobe: {e}")
        return {
            "width": 1920,
            "height": 1080,
            "duration": 0.0,
            "size": video_path.stat().st_size if video_path.exists() else 0,
            "aspect_ratio": 16.0 / 9.0,
        }

def get_video_duration(video_path: Path) -> float:
    info = get_video_info(video_path)
    return info["duration"]

def extract_frame_at(video_path: Path, timestamp: float, output_path: Path) -> bool:
    """
    Extracts a single frame from video at given timestamp using ffmpeg.
    """
    time_str = f"{max(0.0, timestamp):.3f}"
    cmd = [
        "ffmpeg", "-y",
        "-ss", time_str,
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0 and output_path.exists()

def fit_image_with_blurred_bg(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Places image in target dimensions with blurred background fill (similar to Reference Image 3).
    """
    img = img.convert("RGB")
    bg = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(25))

    dimmer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 80))
    bg.paste(dimmer, (0, 0), dimmer)

    orig_w, orig_h = img.size
    ratio = min(target_w / orig_w, target_h / orig_h)
    new_w = max(1, int(orig_w * ratio))
    new_h = max(1, int(orig_h * ratio))
    fg = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    bg.paste(fg, (paste_x, paste_y))

    return bg

def generate_smart_thumbnail(video_path: Path, slug: str, temp_dir: Path) -> Path:
    """
    Generates a dynamic 16:9 composite thumbnail based on video aspect ratio:
    - 9:16 (Ratio < 0.8) -> 3 equal parts, 3 frames side-by-side vertical panels (Ref Image 1)
    - 16:9 (Ratio >= 1.5) -> 4 equal parts, 2x2 grid (Ref Image 2)
    - Other (4:3, 3:4, etc.) -> 6 equal parts, 3x2 grid with sleek cards (Ref Image 3)
    """
    info = get_video_info(video_path)
    duration = info["duration"]
    ratio = info["aspect_ratio"]

    output_path = temp_dir / f"{slug}_composite_thumb.jpg"
    log(f"[Thumbnail] Detected Resolution: {info['width']}x{info['height']} (Ratio: {ratio:.2f}), Duration: {duration:.2f}s")

    effective_dur = duration if duration > 1.0 else 30.0

    # =========================================================================
    # CASE 1: 9:16 Ratio (Portrait / Shorts / Vertical Videos) -> 3 Panels (Ref 1)
    # =========================================================================
    if ratio < 0.8:
        log("[Thumbnail] Mode: 9:16 Ratio -> Creating 3-Panel Side-by-Side Thumbnail (16:9)")
        part = effective_dur / 3.0
        timestamps = [
            0.1 * part,
            part + 0.1 * part,
            2.0 * part + 0.1 * part,
        ]

        frame_imgs = []
        for i, ts in enumerate(timestamps):
            frame_file = temp_dir / f"{slug}_f916_{i}.jpg"
            if extract_frame_at(video_path, ts, frame_file):
                try:
                    frame_imgs.append(Image.open(frame_file).convert("RGB"))
                except Exception:
                    pass

        if not frame_imgs:
            frame_file = temp_dir / f"{slug}_fallback.jpg"
            extract_frame_at(video_path, 0.0, frame_file)
            if frame_file.exists():
                frame_imgs = [Image.open(frame_file).convert("RGB")] * 3

        canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), color=(0, 0, 0))
        divider_w = 8
        col_w = (CANVAS_WIDTH - (2 * divider_w)) // 3
        col_h = CANVAS_HEIGHT

        for idx in range(3):
            img = frame_imgs[idx % len(frame_imgs)]
            cropped = ImageOps.fit(img, (col_w, col_h), method=Image.Resampling.LANCZOS)
            x_pos = idx * (col_w + divider_w)
            canvas.paste(cropped, (x_pos, 0))

        # Explicitly ensure clean black divider lines using 2-point tuple coordinates [(x0, y0), (x1, y1)]
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(col_w, 0), (col_w + divider_w, col_h)], fill=(0, 0, 0))
        draw.rectangle([(2 * col_w + divider_w, 0), (2 * col_w + 2 * divider_w, col_h)], fill=(0, 0, 0))

        canvas.save(output_path, "JPEG", quality=95)
        log(f"[Thumbnail] 9:16 Composite generated: {output_path.name}")
        return output_path

    # =========================================================================
    # CASE 2: 16:9 Ratio (Landscape / Widescreen Videos) -> 4 Panels 2x2 Grid (Ref 2)
    # =========================================================================
    elif ratio >= 1.5:
        log("[Thumbnail] Mode: 16:9 Ratio -> Creating 2x2 Grid Thumbnail (4 Frames, Ref 2)")
        part = effective_dur / 4.0
        timestamps = [
            0.1 * part,
            part + 0.1 * part,
            2.0 * part + 0.1 * part,
            3.0 * part + 0.1 * part,
        ]

        frame_imgs = []
        for i, ts in enumerate(timestamps):
            frame_file = temp_dir / f"{slug}_f169_{i}.jpg"
            if extract_frame_at(video_path, ts, frame_file):
                try:
                    frame_imgs.append(Image.open(frame_file).convert("RGB"))
                except Exception:
                    pass

        if not frame_imgs:
            frame_file = temp_dir / f"{slug}_fallback.jpg"
            extract_frame_at(video_path, 0.0, frame_file)
            if frame_file.exists():
                frame_imgs = [Image.open(frame_file).convert("RGB")] * 4

        canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), color=(0, 0, 0))
        divider = 8
        cell_w = (CANVAS_WIDTH - divider) // 2
        cell_h = (CANVAS_HEIGHT - divider) // 2

        coords = [
            (0, 0),
            (cell_w + divider, 0),
            (0, cell_h + divider),
            (cell_w + divider, cell_h + divider),
        ]

        for idx in range(4):
            img = frame_imgs[idx % len(frame_imgs)]
            cropped = ImageOps.fit(img, (cell_w, cell_h), method=Image.Resampling.LANCZOS)
            canvas.paste(cropped, coords[idx])

        # Draw grid dividing cross with 2-point tuple coordinates [(x0, y0), (x1, y1)]
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(cell_w, 0), (cell_w + divider, CANVAS_HEIGHT)], fill=(0, 0, 0))
        draw.rectangle([(0, cell_h), (CANVAS_WIDTH, cell_h + divider)], fill=(0, 0, 0))

        canvas.save(output_path, "JPEG", quality=95)
        log(f"[Thumbnail] 16:9 Composite generated: {output_path.name}")
        return output_path

    # =========================================================================
    # CASE 3: Other Ratios (4:3, 3:4, 1:1, etc.) -> 6 Panels 3x2 Grid (Ref 3)
    # =========================================================================
    else:
        log("[Thumbnail] Mode: Other Ratio -> Creating 3x2 Grid Thumbnail (6 Frames, Ref 3)")
        part = effective_dur / 6.0
        timestamps = [
            0.1 * part,
            1.0 * part + 0.1 * part,
            2.0 * part + 0.1 * part,
            3.0 * part + 0.1 * part,
            4.0 * part + 0.1 * part,
            5.0 * part + 0.1 * part,
        ]

        frame_imgs = []
        for i, ts in enumerate(timestamps):
            frame_file = temp_dir / f"{slug}_fother_{i}.jpg"
            if extract_frame_at(video_path, ts, frame_file):
                try:
                    frame_imgs.append(Image.open(frame_file).convert("RGB"))
                except Exception:
                    pass

        if not frame_imgs:
            frame_file = temp_dir / f"{slug}_fallback.jpg"
            extract_frame_at(video_path, 0.0, frame_file)
            if frame_file.exists():
                frame_imgs = [Image.open(frame_file).convert("RGB")] * 6

        bg_color = (20, 24, 33)
        canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), color=bg_color)

        pad_x = 24
        pad_y = 20
        gap = 16
        card_w = (CANVAS_WIDTH - (2 * pad_x) - (2 * gap)) // 3
        card_h = (CANVAS_HEIGHT - (2 * pad_y) - (1 * gap)) // 2

        positions = [
            (pad_x + 0 * (card_w + gap), pad_y + 0 * (card_h + gap)),
            (pad_x + 1 * (card_w + gap), pad_y + 0 * (card_h + gap)),
            (pad_x + 2 * (card_w + gap), pad_y + 0 * (card_h + gap)),
            (pad_x + 0 * (card_w + gap), pad_y + 1 * (card_h + gap)),
            (pad_x + 1 * (card_w + gap), pad_y + 1 * (card_h + gap)),
            (pad_x + 2 * (card_w + gap), pad_y + 1 * (card_h + gap)),
        ]

        for idx in range(6):
            img = frame_imgs[idx % len(frame_imgs)]
            card = fit_image_with_blurred_bg(img, card_w, card_h)

            card_draw = ImageDraw.Draw(card)
            card_draw.rectangle([(0, 0), (card_w - 1, card_h - 1)], outline=(255, 255, 255), width=3)

            canvas.paste(card, positions[idx])

        canvas.save(output_path, "JPEG", quality=95)
        log(f"[Thumbnail] 3x2 Composite generated: {output_path.name}")
        return output_path
