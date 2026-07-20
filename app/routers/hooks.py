import os
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from app.db import SessionLocal, Hook
from app.auth import get_current_token
from app.scrapers.reddit import fetch_reddit

router = APIRouter(prefix="/api/hooks", dependencies=[Depends(get_current_token)])


class HookIn(BaseModel):
    text: str
    source: str = "manual"
    tags: str = ""


@router.get("")
def list_hooks(source: str | None = Query(default=None)):
    with SessionLocal() as s:
        q = select(Hook)
        if source:
            q = q.where(Hook.source == source)
        rows = s.scalars(q.order_by(Hook.created_at.desc())).all()
        return [_serialize(h) for h in rows]


@router.post("", status_code=201)
def create_hook(payload: HookIn):
    with SessionLocal() as s:
        h = Hook(text=payload.text, source=payload.source, tags=payload.tags)
        s.add(h)
        s.commit()
        s.refresh(h)
        return _serialize(h)


@router.get("/reddit")
def reddit_hooks(query: str = "motivacion", limit: int = 10):
    items = fetch_reddit(query, limit)
    # No persistimos automáticamente: el frontend decide qué guardar.
    return items


def _serialize(h: Hook):
    return {
        "id": h.id,
        "text": h.text,
        "source": h.source,
        "tags": h.tags,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }
