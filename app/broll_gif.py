"""Broll de fondo: GIFs de GIPHY (API gratuita, licenciada para reinsertar en
contenido de terceros - a diferencia de scrapear video de YouTube/sitios
random, que puede generar un claim de copyright en un canal monetizado) segun
la palabra clave del segmento/vehiculo. Cache en disco por keyword."""
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

import requests

GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY", "")
GIPHY_CACHE_DIR = Path(os.getenv("GIPHY_CACHE_DIR", "./giphy_cache"))
GIPHY_SEARCH_URL = "https://api.giphy.com/v1/gifs/search"


def _slug(text: str) -> str:
    s = unicodedata.normalize("NFD", text.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or hashlib.md5(text.encode()).hexdigest()[:10]


def get_broll_gif(keyword: str) -> Path | None:
    """GIF cacheado en disco para esta keyword. None si no hay API key o no
    se encontro nada (el caller degrada: sin broll para ese segmento)."""
    if not GIPHY_API_KEY or not keyword:
        return None

    slug = _slug(keyword)
    dst = GIPHY_CACHE_DIR / f"{slug}.gif"
    if dst.exists():
        return dst

    try:
        resp = requests.get(GIPHY_SEARCH_URL, params={
            "api_key": GIPHY_API_KEY, "q": keyword, "limit": 1,
            "rating": "pg-13", "lang": "es",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return None
        gif_url = data[0]["images"]["original"]["url"]
        gif_bytes = requests.get(gif_url, timeout=30).content
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(gif_bytes)
        return dst
    except Exception as e:
        print(f"[broll_gif] fallo buscando '{keyword}': {e}")
        return None
