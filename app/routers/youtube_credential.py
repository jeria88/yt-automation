import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.db import SessionLocal, YoutubeCredential
from app.auth import get_current_token

router = APIRouter(prefix="/api/youtube-credential", dependencies=[Depends(get_current_token)])


class CredentialIn(BaseModel):
    channel_id: str
    channel_title: str
    access_token: str
    refresh_token: str
    expires_in: int = 3600


@router.post("")
def save_credential(payload: CredentialIn):
    """Upsert de la unica credencial YouTube (un canal, sin multi-tenant)."""
    with SessionLocal() as s:
        cred = s.query(YoutubeCredential).first()
        if not cred:
            cred = YoutubeCredential()
            s.add(cred)
        cred.channel_id = payload.channel_id
        cred.channel_title = payload.channel_title
        cred.access_token = payload.access_token
        cred.refresh_token = payload.refresh_token
        cred.expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=payload.expires_in)
        cred.updated_at = datetime.datetime.utcnow()
        s.commit()
        return {"status": "saved", "channel_title": cred.channel_title}


@router.get("")
def get_credential():
    with SessionLocal() as s:
        cred = s.query(YoutubeCredential).first()
        if not cred:
            return {"connected": False}
        return {
            "connected": True,
            "channel_id": cred.channel_id,
            "channel_title": cred.channel_title,
            "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
        }
