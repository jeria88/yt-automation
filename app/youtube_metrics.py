"""Metricas por video publicado. v1: views/likes/comments via videos.list
(mismo scope youtube.readonly ya autorizado). CTR/impresiones/retencion real
necesitan el scope yt-analytics.readonly (pendiente - requeriria re-autorizar
de nuevo, ver PROGRESS.md)."""
from app.youtube_oauth import ensure_fresh_access_token


def fetch_stats(video_id: str) -> dict:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

    token = ensure_fresh_access_token()
    youtube = build("youtube", "v3", credentials=Credentials(token=token))
    resp = youtube.videos().list(part="statistics", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError(f"video {video_id} no encontrado")
    stats = items[0]["statistics"]
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
    }


def save_snapshot(pipeline_id: int, video_id: str) -> dict:
    from app.db import SessionLocal, VideoMetrics

    stats = fetch_stats(video_id)
    with SessionLocal() as s:
        m = VideoMetrics(reel_pipeline_id=pipeline_id, views=stats["views"], likes=stats["likes"])
        s.add(m)
        s.commit()
    return stats
