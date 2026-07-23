"""Regenera titulo/descripcion/miniatura de un video ya publicado que no
performa, y lo actualiza EN EL MISMO video de YouTube (no re-sube) - mantiene
vistas/comentarios acumulados, que un re-upload perderia a cero."""
from app.metadata_gen import generate_metadata
from app.thumbnail_gen import generate_thumbnail
from app.youtube_oauth import ensure_fresh_access_token


def regenerate_and_update(video_id: str, script_text: str, rendered_video_path: str, thumbnail_out: str) -> dict:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    meta = generate_metadata(script_text)
    generate_thumbnail(rendered_video_path, meta["title"], thumbnail_out)

    token = ensure_fresh_access_token()
    youtube = build("youtube", "v3", credentials=Credentials(token=token))

    current = youtube.videos().list(part="snippet", id=video_id).execute()["items"][0]["snippet"]
    current["title"] = meta["title"][:100]
    current["description"] = meta["description"][:5000]
    youtube.videos().update(part="snippet", body={"id": video_id, "snippet": current}).execute()
    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_out)).execute()

    return meta
