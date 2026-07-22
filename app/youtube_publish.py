"""Publicacion en YouTube - resumable upload con titulo/descripcion/miniatura.
Adaptado de content-studio/agents/youtube_publish.py, credenciales propias
(ensure_fresh_access_token) en vez de las del tenant."""
from app.youtube_oauth import ensure_fresh_access_token


def publish(video_path: str, title: str, description: str, thumbnail_path: str | None = None,
            privacy: str = "public") -> dict:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    token = ensure_fresh_access_token()
    youtube = build("youtube", "v3", credentials=Credentials(token=token))

    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=4 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(
        part="id,snippet,status",
        notifySubscribers=True,
        body={
            "snippet": {"title": title[:100], "description": description[:5000]},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        },
        media_body=media,
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    if thumbnail_path:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()

    return {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
