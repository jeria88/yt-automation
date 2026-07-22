import os
import re
from pathlib import Path

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.backlog import fill_backlog, regenerate_script
from app.db import SessionLocal, ReelPipeline
from app.telegram_bot import answer_callback_query, download_voice, send_message

router = APIRouter(prefix="/telegram")

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/webhook")
async def webhook(request: Request):
    update = await request.json()

    if "callback_query" in update:
        _handle_callback(update["callback_query"])
    elif "message" in update:
        _handle_message(update["message"])

    return {"ok": True}


def _handle_callback(cbq: dict) -> None:
    answer_callback_query(cbq["id"])
    data = cbq.get("data", "")
    if data.startswith("regen:"):
        pipeline_id = int(data.split(":", 1)[1])
        regenerate_script(pipeline_id)


def _handle_message(msg: dict) -> None:
    chat_id = str(msg["chat"]["id"])

    if "voice" in msg:
        _handle_voice(chat_id, msg["voice"], msg)
    elif "audio" in msg:
        _handle_voice(chat_id, msg["audio"], msg)
    elif "document" in msg and (msg["document"].get("mime_type") or "").startswith("audio/"):
        _handle_voice(chat_id, msg["document"], msg)
    elif msg.get("text") == "/start":
        send_message(chat_id, "Hola! Soy el bot de ReyPirataChaman. Te voy a mandar guiones propuestos para que grabes tu voz.")
    elif msg.get("text") == "/nuevo":
        fill_backlog()


def _extract_pipeline_id(msg: dict) -> int | None:
    """Prioridad: 1) responder nativo a un mensaje de guion, 2) numero en el
    texto/caption ("3", "#3", "guion 3"). Si ninguno matchea, None (fallback
    al pendiente mas reciente)."""
    reply = msg.get("reply_to_message")
    if reply and "message_id" in reply:
        with SessionLocal() as s:
            r = s.scalar(
                select(ReelPipeline).where(
                    ReelPipeline.telegram_script_message_id == str(reply["message_id"])
                )
            )
            if r:
                return r.id

    caption = msg.get("caption") or msg.get("text") or ""
    m = re.search(r"\d+", caption)
    if m:
        return int(m.group())

    return None


def _handle_voice(chat_id: str, voice: dict, msg: dict) -> None:
    explicit_id = _extract_pipeline_id(msg)

    with SessionLocal() as s:
        if explicit_id is not None:
            r = s.scalar(
                select(ReelPipeline).where(
                    ReelPipeline.id == explicit_id,
                    ReelPipeline.telegram_chat_id == chat_id,
                    ReelPipeline.status == "awaiting_audio",
                )
            )
            if not r:
                send_message(chat_id, f"No tengo el guion #{explicit_id} esperando audio (¿ya lo mandaste, o no existe?).")
                return
        else:
            r = s.scalar(
                select(ReelPipeline)
                .where(ReelPipeline.telegram_chat_id == chat_id, ReelPipeline.status == "awaiting_audio")
                .order_by(ReelPipeline.updated_at.desc())
            )
            if not r:
                send_message(chat_id, "No tengo ningún guion esperando audio ahora mismo.")
                return
        pipeline_id = r.id

    audio_path = AUDIO_DIR / f"{pipeline_id}.ogg"
    download_voice(voice["file_id"], str(audio_path))

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.audio_file_path = str(audio_path)
        r.audio_duration_seconds = voice.get("duration")
        r.status = "audio_received"
        r.telegram_audio_message_id = None
        s.commit()

    send_message(chat_id, f"🎙️ Audio recibido para el guion #{pipeline_id}. Armando el storyboard...")
