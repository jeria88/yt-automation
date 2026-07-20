from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from app.db import SessionLocal, Video
from app.auth import get_current_token

router = APIRouter(prefix="/api/videos", dependencies=[Depends(get_current_token)])

STAGES = ["idea", "guion", "audio", "edicion", "miniatura", "publicado"]


class VideoIn(BaseModel):
    title: str
    stage: str = "idea"
    hook_id: Optional[int] = None
    notes: str = ""
    due: Optional[str] = None  # ISO datetime

    @field_validator("stage")
    @classmethod
    def _valid_stage(cls, v):
        if v not in STAGES:
            raise ValueError(f"stage debe ser uno de {STAGES}")
        return v


class VideoPatch(BaseModel):
    stage: str

    @field_validator("stage")
    @classmethod
    def _valid_stage(cls, v):
        if v not in STAGES:
            raise ValueError(f"stage debe ser uno de {STAGES}")
        return v


@router.get("")
def list_videos():
    with SessionLocal() as s:
        rows = s.scalars(select(Video).order_by(Video.created_at.desc())).all()
        return [_serialize(v) for v in rows]


@router.post("", status_code=201)
def create_video(payload: VideoIn):
    with SessionLocal() as s:
        v = Video(
            title=payload.title,
            stage=payload.stage,
            hook_id=payload.hook_id,
            notes=payload.notes,
            due=_parse_dt(payload.due),
        )
        s.add(v)
        s.commit()
        s.refresh(v)
        return _serialize(v)


@router.patch("/{video_id}")
def update_stage(video_id: int, payload: VideoPatch):
    with SessionLocal() as s:
        v = s.get(Video, video_id)
        if not v:
            raise HTTPException(404, "video no encontrado")
        v.stage = payload.stage
        s.commit()
        s.refresh(v)
        return _serialize(v)


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _serialize(v: Video):
    return {
        "id": v.id,
        "title": v.title,
        "stage": v.stage,
        "hook_id": v.hook_id,
        "notes": v.notes,
        "due": v.due.isoformat() if v.due else None,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }
