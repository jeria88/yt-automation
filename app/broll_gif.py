"""Broll de fondo: video stock real (Pexels primero, Pixabay de respaldo) segun
la palabra clave del segmento. Cache en disco por keyword.

Reemplaza GIPHY (feedback Franco: los "gifs" de GIPHY para keywords de
introspeccion/autoayuda son memes/quote-cards, no b-roll - verificado en vivo,
ver bitacora). Patron adoptado de los 2 generadores de shorts open source mas
usados que existen (MoneyPrinterTurbo 98.8k stars, ShortGPT 7.7k stars): ambos
usan Pexels/Pixabay para video de stock real en vez de gifs, con keywords LLM
concretas y visuales en vez de abstractas (ver storyboard.py)."""
import hashlib
import os
import re
import unicodedata
from pathlib import Path

import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
BROLL_CACHE_DIR = Path(os.getenv("BROLL_CACHE_DIR", "./broll_cache"))
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"
MIN_DURATION_SECONDS = 4


def _slug(text: str) -> str:
    s = unicodedata.normalize("NFD", text.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or hashlib.md5(text.encode()).hexdigest()[:10]


def _best_pexels_url(video: dict) -> str | None:
    """El archivo de mejor calidad hasta 1080p de ancho (evita 4K, mas pesado
    de lo que necesita un short vertical)."""
    files = sorted(
        (f for f in video.get("video_files", []) if f.get("width")),
        key=lambda f: f["width"],
        reverse=True,
    )
    for f in files:
        if f["width"] <= 1080:
            return f["link"]
    return files[-1]["link"] if files else None


def _search_pexels(keyword: str) -> str | None:
    if not PEXELS_API_KEY:
        return None
    try:
        resp = requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": keyword, "per_page": 5, "orientation": "portrait"},
            timeout=15,
        )
        resp.raise_for_status()
        for video in resp.json().get("videos", []):
            if video.get("duration", 0) >= MIN_DURATION_SECONDS:
                url = _best_pexels_url(video)
                if url:
                    return url
    except Exception as e:
        print(f"[broll] pexels fallo buscando '{keyword}': {e}")
    return None


def _search_pixabay(keyword: str) -> str | None:
    if not PIXABAY_API_KEY:
        return None
    try:
        resp = requests.get(
            PIXABAY_SEARCH_URL,
            params={"key": PIXABAY_API_KEY, "q": keyword, "video_type": "film", "per_page": 5},
            timeout=15,
        )
        resp.raise_for_status()
        for hit in resp.json().get("hits", []):
            if hit.get("duration", 0) < MIN_DURATION_SECONDS:
                continue
            videos = hit.get("videos", {})
            video = videos.get("medium") or videos.get("small") or videos.get("large")
            if video and video.get("url"):
                return video["url"]
    except Exception as e:
        print(f"[broll] pixabay fallo buscando '{keyword}': {e}")
    return None


def get_broll_video(keyword: str) -> Path | None:
    """Clip de stock cacheado en disco para esta keyword. None si no hay
    ninguna key configurada o no se encontro nada (el caller degrada: sin
    broll para ese segmento)."""
    if not keyword or not (PEXELS_API_KEY or PIXABAY_API_KEY):
        return None

    slug = _slug(keyword)
    dst = BROLL_CACHE_DIR / f"{slug}.mp4"
    if dst.exists():
        return dst

    video_url = _search_pexels(keyword) or _search_pixabay(keyword)
    if not video_url:
        return None

    try:
        video_bytes = requests.get(video_url, timeout=30).content
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(video_bytes)
        return dst
    except Exception as e:
        print(f"[broll] fallo descargando '{keyword}': {e}")
        return None
