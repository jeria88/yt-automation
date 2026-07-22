from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from app.db import SessionLocal, ReelPipeline
from app.auth import get_current_token
from app.backlog import fill_backlog

router = APIRouter(prefix="/api/reel-pipeline", dependencies=[Depends(get_current_token)])

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
        "rendered_video_path": r.rendered_video_path,
        "youtube_video_id": r.youtube_video_id,
        "youtube_url": r.youtube_url,
        "youtube_privacy_status": r.youtube_privacy_status,
        "last_error": r.last_error,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
