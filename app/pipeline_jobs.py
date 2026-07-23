"""Jobs disparados en background por el webhook de Telegram y por el pipeline
de render (Fase 3, 5 y 7)."""
import datetime
import json
import logging
import os
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal, ReelPipeline
from app.hook_regen import regenerate_and_update
from app.metadata_gen import generate_metadata
from app.storyboard import build_storyboard
from app.telegram_bot import send_message
from app.youtube_metrics import save_snapshot
from app.youtube_publish import publish

logger = logging.getLogger(__name__)

# A8 del plan: sin datos historicos para calibrar, arranca con un piso bajo
# (canal nuevo). Recalibrar con datos reales una vez haya trafico.
PERFORMANCE_WINDOW_HOURS = int(os.getenv("PERFORMANCE_WINDOW_HOURS", "48"))
MIN_VIEWS_THRESHOLD = int(os.getenv("MIN_VIEWS_THRESHOLD", "20"))
MAX_HOOK_REGENS = int(os.getenv("MAX_HOOK_REGENS", "1"))


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
        r.updated_at = datetime.datetime.utcnow()  # marca el "publicado en" para la ventana de Fase 7
        s.commit()

    if chat_id:
        send_message(chat_id, f"🚀 Video #{pipeline_id} publicado: {result['url']}")


def check_performance_and_regen(pipeline_id: int) -> str:
    """Si el video lleva PERFORMANCE_WINDOW_HOURS publicado, mide vistas y,
    si no llega al piso, regenera titulo/descripcion/miniatura EN EL MISMO
    video (no re-sube - mantiene vistas/comentarios acumulados)."""
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r or r.status != "published" or not r.youtube_video_id:
            return "skip"
        age_hours = (datetime.datetime.utcnow() - r.updated_at).total_seconds() / 3600
        if age_hours < PERFORMANCE_WINDOW_HOURS:
            return "too_soon"
        chat_id = r.telegram_chat_id
        video_id = r.youtube_video_id
        script = r.script_text
        video_path = r.rendered_video_path
        hook_variant = r.hook_variant

    stats = save_snapshot(pipeline_id, video_id)

    if stats["views"] >= MIN_VIEWS_THRESHOLD or hook_variant > MAX_HOOK_REGENS:
        with SessionLocal() as s:
            r = s.get(ReelPipeline, pipeline_id)
            r.status = "monitoring"
            s.commit()
        return "kept"

    try:
        thumb_out = str(Path(video_path).with_suffix("")) + f"_thumb_v{hook_variant + 1}.jpg"
        meta = regenerate_and_update(video_id, script, video_path, thumb_out)
    except Exception as e:
        logger.exception("Fallo regenerando gancho de pipeline %s", pipeline_id)
        with SessionLocal() as s:
            r = s.get(ReelPipeline, pipeline_id)
            r.status = "monitoring"
            r.last_error = f"hook_regen: {e}"
            s.commit()
        if chat_id:
            send_message(chat_id, f"⚠️ Video #{pipeline_id} no llegó a {MIN_VIEWS_THRESHOLD} vistas en {PERFORMANCE_WINDOW_HOURS}h, pero no pude regenerar el gancho: {e}")
        return "regen_failed"

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.title = meta["title"]
        r.description = meta["description"]
        r.hook_variant = hook_variant + 1
        r.status = "monitoring"
        r.updated_at = datetime.datetime.utcnow()
        s.commit()

    if chat_id:
        send_message(
            chat_id,
            f"📉 Video #{pipeline_id} tenía {stats['views']} vistas en {PERFORMANCE_WINDOW_HOURS}h "
            f"(piso: {MIN_VIEWS_THRESHOLD}) — cambié el título/miniatura sin re-subir: \"{meta['title']}\"",
        )
    return "regenerated"


def check_all_published() -> list[dict]:
    with SessionLocal() as s:
        ids = [r.id for r in s.scalars(select(ReelPipeline).where(ReelPipeline.status == "published"))]
    return [{"id": pid, "result": check_performance_and_regen(pid)} for pid in ids]
