"""Jobs disparados en background por el webhook de Telegram y por el pipeline
de render (Fase 3 y Fase 5)."""
import json
import logging

from app.db import SessionLocal, ReelPipeline
from app.metadata_gen import generate_metadata
from app.storyboard import build_storyboard
from app.telegram_bot import send_message
from app.youtube_publish import publish

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


def publish_pipeline(pipeline_id: int) -> None:
    """Tras el render: genera titulo/descripcion y publica a YouTube automatico,
    sin gate (decision de Franco - ver plan)."""
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r or r.status != "render_ready":
            return
        chat_id = r.telegram_chat_id
        script = r.script_text
        video_path = r.rendered_video_path
        thumbnail_path = r.thumbnail_path
        r.status = "publishing"
        s.commit()

    try:
        meta = generate_metadata(script)
        with SessionLocal() as s:
            r = s.get(ReelPipeline, pipeline_id)
            r.title = meta["title"]
            r.description = meta["description"]
            s.commit()
        result = publish(video_path, meta["title"], meta["description"], thumbnail_path)
    except Exception as e:
        logger.exception("Fallo publicando pipeline %s", pipeline_id)
        with SessionLocal() as s:
            r = s.get(ReelPipeline, pipeline_id)
            r.status = "error"
            r.last_error = f"publish: {e}"
            s.commit()
        if chat_id:
            send_message(chat_id, f"⚠️ No pude publicar el video #{pipeline_id} en YouTube: {e}")
        return

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.status = "published"
        r.youtube_video_id = result["video_id"]
        r.youtube_url = result["url"]
        s.commit()

    if chat_id:
        send_message(chat_id, f"🚀 Video #{pipeline_id} publicado: {result['url']}")
