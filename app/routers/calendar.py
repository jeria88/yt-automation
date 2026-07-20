import os
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from app.db import SessionLocal, Post, Video
from app.auth import get_current_token

router = APIRouter(prefix="/api/posts", dependencies=[Depends(get_current_token)])


class PostIn(BaseModel):
    video_id: int
    scheduled_at: str | None = None  # ISO
    status: str = "planned"
    platform: str = "youtube"


@router.get("")
def list_posts():
    with SessionLocal() as s:
        rows = s.scalars(select(Post).order_by(Post.scheduled_at.asc().nullslast())).all()
        return [_serialize(p) for p in rows]


@router.post("", status_code=201)
def create_post(payload: PostIn):
    with SessionLocal() as s:
        p = Post(
            video_id=payload.video_id,
            scheduled_at=_parse(payload.scheduled_at),
            status=payload.status,
            platform=payload.platform,
        )
        s.add(p)
        s.commit()
        s.refresh(p)
        return _serialize(p)


def _parse(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _serialize(p: Post):
    return {
        "id": p.id,
        "video_id": p.video_id,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "status": p.status,
        "platform": p.platform,
    }
