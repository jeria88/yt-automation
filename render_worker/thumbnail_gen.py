"""Miniatura sin tokens pagos: frame del video ya renderizado + texto superpuesto
con Pillow. Corre en el render worker (bare host, tiene ffmpeg + fuentes)."""
import subprocess
from pathlib import Path

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def generate_thumbnail(video_path: str, title: str, out_path: str, frame_at_seconds: float = 2.0) -> str:
    from PIL import Image, ImageDraw, ImageFont

    tmp_frame = str(Path(out_path).with_suffix(".raw.jpg"))
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(frame_at_seconds), "-i", video_path, "-frames:v", "1", tmp_frame],
        check=True, capture_output=True,
    )

    img = Image.open(tmp_frame).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_size = int(w * 0.075)
    font = ImageFont.truetype(FONT_PATH, font_size)

    words = title.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) > w * 0.88:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    lines = lines[:3]

    line_height = int(font_size * 1.2)
    total_height = line_height * len(lines) + 60
    y = h - total_height - 40

    draw.rectangle([0, y - 20, w, h], fill=(0, 0, 0, 160))
    for i, line in enumerate(lines):
        tw = draw.textlength(line, font=font)
        draw.text(((w - tw) / 2, y + i * line_height), line, font=font, fill=(240, 232, 220))

    img.save(out_path, "JPEG", quality=90)
    Path(tmp_frame).unlink(missing_ok=True)
    return out_path
