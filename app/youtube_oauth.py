"""OAuth de YouTube para el canal de ReyPirataChaman - una sola cuenta, sin
multi-tenant. Adaptado de content-studio/api/google_oauth.py (mismo riesgo ya
documentado ahi: consent screen en Testing -> refresh token caduca a los 7
dias)."""
import os

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()


def ensure_fresh_access_token() -> str:
    """Devuelve un access_token valido, refrescando si esta vencido. Lee/escribe
    la unica fila de YoutubeCredential."""
    import datetime
    from app.db import SessionLocal, YoutubeCredential

    with SessionLocal() as s:
        cred = s.query(YoutubeCredential).first()
        if not cred:
            raise RuntimeError("No hay YoutubeCredential guardado - correr el setup de OAuth primero")
        if cred.expires_at and cred.expires_at > datetime.datetime.utcnow() + datetime.timedelta(minutes=5):
            return cred.access_token

        tok = refresh_access_token(cred.refresh_token)
        cred.access_token = tok["access_token"]
        cred.expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=tok.get("expires_in", 3600))
        cred.updated_at = datetime.datetime.utcnow()
        s.commit()
        return cred.access_token
