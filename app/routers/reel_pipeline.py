import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from app.db import SessionLocal, ReelPipeline
from app.auth import get_current_token
from app.backlog import fill_backlog
from app.pipeline_jobs import process_audio, publish_pipeline

router = APIRouter(prefix="/api/reel-pipeline", dependencies=[Depends(get_current_token)])

RENDER_DIR = Path(os.getenv("RENDER_DIR", "./renders"))
RENDER_DIR.mkdir(parents=True, exist_ok=True)

STATUSES = [
    "topic_pending", "script_pending", "script_sent", "awaiting_audio", "audio_received",
    "storyboard_pending", "storyboard_ready", "rendering", "render_ready",
    "publishing", "published", "monitoring", "regenerating_hook", "republishing", "error",
]


class ReelPipelineIn(BaseModel):
    video_id: Optional[int] = None
    topic_source: Optional[str] = None
    script_text: Optional[str] = None


class ReelPipelinePatch(BaseModel):
    status: str
    last_error: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v):
        if v not in STATUSES:
            raise ValueError(f"status debe ser uno de {STATUSES}")
        return v


@router.get("")
def list_pipeline(status: Optional[str] = None):
    with SessionLocal() as s:
        q = select(ReelPipeline).order_by(ReelPipeline.created_at.desc())
        if status:
            q = q.where(ReelPipeline.status == status)
        rows = s.scalars(q).all()
        return [_serialize(r) for r in rows]


@router.post("", status_code=201)
def create_pipeline_entry(payload: ReelPipelineIn):
    with SessionLocal() as s:
        r = ReelPipeline(
            video_id=payload.video_id,
            topic_source=payload.topic_source,
            script_text=payload.script_text,
        )
        s.add(r)
        s.commit()
        s.refresh(r)
        return _serialize(r)


@router.get("/{pipeline_id}")
def get_pipeline_entry(pipeline_id: int):
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            raise HTTPException(404, "reel_pipeline no encontrado")
        return _serialize(r)


@router.patch("/{pipeline_id}")
def update_status(pipeline_id: int, payload: ReelPipelinePatch):
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            raise HTTPException(404, "reel_pipeline no encontrado")
        r.status = payload.status
        if payload.last_error is not None:
            r.last_error = payload.last_error
        s.commit()
        s.refresh(r)
        return _serialize(r)


@router.post("/fill-backlog")
def trigger_fill_backlog():
    created = fill_backlog()
    return {"created": created}


@router.post("/{pipeline_id}/retry-storyboard")
def retry_storyboard(pipeline_id: int, background_tasks: BackgroundTasks):
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            raise HTTPException(404, "reel_pipeline no encontrado")
        if not r.audio_file_path:
            raise HTTPException(409, "este guion todavia no tiene audio")
        r.status = "audio_received"
        r.last_error = None
        s.commit()
    background_tasks.add_task(process_audio, pipeline_id)
    return {"status": "retrying"}


@router.post("/{pipeline_id}/publish")
def trigger_publish(pipeline_id: int, background_tasks: BackgroundTasks):
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            raise HTTPException(404, "reel_pipeline no encontrado")
        if r.status != "render_ready":
            raise HTTPException(409, f"status es '{r.status}', no 'render_ready'")
    background_tasks.add_task(publish_pipeline, pipeline_id)
    return {"status": "publishing"}


@router.get("/{pipeline_id}/audio")
def get_audio(pipeline_id: int):
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r or not r.audio_file_path or not os.path.exists(r.audio_file_path):
            raise HTTPException(404, "audio no encontrado")
        path = r.audio_file_path
    return FileResponse(path, media_type="audio/ogg")


@router.post("/{pipeline_id}/render-complete")
async def render_complete(pipeline_id: int, background_tasks: BackgroundTasks,
                           file: UploadFile, thumbnail: Optional[UploadFile] = None):
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            raise HTTPException(404, "reel_pipeline no encontrado")

    dst = RENDER_DIR / f"{pipeline_id}.mp4"
    with open(dst, "wb") as f:
        f.write(await file.read())

    thumb_dst = None
    if thumbnail is not None:
        thumb_dst = RENDER_DIR / f"{pipeline_id}_thumb.jpg"
        with open(thumb_dst, "wb") as f:
            f.write(await thumbnail.read())

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.rendered_video_path = str(dst)
        if thumb_dst:
            r.thumbnail_path = str(thumb_dst)
        r.status = "render_ready"
        s.commit()

    background_tasks.add_task(publish_pipeline, pipeline_id)
    return {"status": "render_ready"}


def _serialize(r: ReelPipeline):
    return {
        "id": r.id,
        "video_id": r.video_id,
        "status": r.status,
        "topic_source": r.topic_source,
        "script_text": r.script_text,
        "hook_variant": r.hook_variant,
        "audio_file_path": r.audio_file_path,
        "audio_duration_seconds": r.audio_duration_seconds,
        "storyboard_json": r.storyboard_json,
        "title": r.title,
        "description": r.description,
        "thumbnail_path": r.thumbnail_path,
        "rendered_video_path": r.rendered_video_path,
        "youtube_video_id": r.youtube_video_id,
        "youtube_url": r.youtube_url,
        "youtube_privacy_status": r.youtube_privacy_status,
        "last_error": r.last_error,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
