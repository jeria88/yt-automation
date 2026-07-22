"""Jobs disparados en background por el webhook de Telegram (Fase 3)."""
import json
import logging

from app.db import SessionLocal, ReelPipeline
from app.storyboard import build_storyboard
from app.telegram_bot import send_message

logger = logging.getLogger(__name__)


def process_audio(pipeline_id: int) -> None:
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            return
        chat_id = r.telegram_chat_id
        script = r.script_text
        audio_path = r.audio_file_path
        r.status = "storyboard_pending"
        s.commit()

    try:
        storyboard = build_storyboard(script, audio_path)
    except Exception as e:
        logger.exception("Fallo armando storyboard para pipeline %s", pipeline_id)
        with SessionLocal() as s:
            r = s.get(ReelPipeline, pipeline_id)
            r.status = "error"
            r.last_error = f"storyboard: {e}"
            s.commit()
        send_message(chat_id, f"⚠️ No pude armar el storyboard del guion #{pipeline_id}: {e}")
        return

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.storyboard_json = json.dumps(storyboard, ensure_ascii=False)
        r.status = "storyboard_ready"
        s.commit()

    resumen = "\n".join(
        f"  {seg['start']:.0f}-{seg['end']:.0f}s: {seg['vehiculo']}"
        for seg in storyboard["segments"]
    )
    send_message(
        chat_id,
        f"🎬 Storyboard del guion #{pipeline_id} listo:\n{resumen}\n\n"
        f"Sigue solo hacia el render, no hace falta que apruebes — avisame en los "
        f"próximos minutos si querés cortarlo.",
        buttons=[[("✂️ Cortar", f"cut:{pipeline_id}")]],
    )
