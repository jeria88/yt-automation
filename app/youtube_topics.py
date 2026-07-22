"""Fuente de temáticas: YouTube Data API acotada al nicho del canal.
No usa el chart mostPopular (trae virales sin relación al nicho)."""
import os
import random

import httpx

NICHE_KEYWORDS = [k.strip() for k in os.getenv(
    "NICHE_KEYWORDS", "conciencia,viaje interior,meditación,desarrollo personal"
).split(",") if k.strip()]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def pick_topic() -> dict:
    """Busca videos recientes y relevantes en una keyword al azar del nicho,
    devuelve el mas visto/relevante como semilla de tematica."""
    key = os.environ["YOUTUBE_API_KEY"]
    keyword = random.choice(NICHE_KEYWORDS)
    resp = httpx.get(
        SEARCH_URL,
        params={
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "relevance",
            "relevanceLanguage": "es",
            "maxResults": 10,
            "key": key,
        },
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        return {"keyword": keyword, "title": keyword, "description": ""}
    pick = random.choice(items)
    return {
        "keyword": keyword,
        "title": pick["snippet"]["title"],
        "description": pick["snippet"]["description"],
    }
