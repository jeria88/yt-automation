from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.db import SessionLocal, Video, Post
from app.auth import get_current_token

router = APIRouter(prefix="/api/stats", dependencies=[Depends(get_current_token)])


@router.get("")
def stats():
    with SessionLocal() as s:
        total = s.scalar(select(func.count()).select_from(Video))
        by_stage = {}
        rows = s.execute(
            select(Video.stage, func.count()).group_by(Video.stage)
        ).all()
        for stage, count in rows:
            by_stage[stage] = count

        now = datetime.utcnow()
        upcoming = s.scalars(
            select(Post)
            .where(Post.scheduled_at >= now)
            .order_by(Post.scheduled_at.asc())
            .limit(10)
        ).all()
        upcoming_list = [
            {"video_id": p.video_id, "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None}
            for p in upcoming
        ]
        return {"total": total, "by_stage": by_stage, "upcoming": upcoming_list}
