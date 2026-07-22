"""Mantiene el backlog de guiones propuestos lleno. Se dispara via endpoint
(cron/systemd timer externo lo llama periodicamente, ver Fase 2 del plan)."""
import os

from sqlalchemy import select, func

from app.db import SessionLocal, ReelPipeline
from app.script_gen import generate_from_topic
from app.telegram_bot import send_message
from app.youtube_topics import pick_topic

BACKLOG_MIN_PENDING = int(os.getenv("BACKLOG_MIN_PENDING", "3"))


def pending_count() -> int:
    with SessionLocal() as s:
        return s.scalar(
            select(func.count(ReelPipeline.id)).where(
                ReelPipeline.status.in_(["script_pending", "script_sent", "awaiting_audio"])
            )
        )


def fill_backlog() -> list[int]:
    created = []
    while pending_count() < BACKLOG_MIN_PENDING:
        created.append(_create_and_send_one())
    return created


def _create_and_send_one() -> int:
    chat_id = os.environ["TELEGRAM_CHAT_ID_RPC"]
    topic = pick_topic()
    script = generate_from_topic(topic)

    with SessionLocal() as s:
        r = ReelPipeline(
            status="script_pending",
            topic_source=f"youtube_search:{topic['keyword']}",
            script_text=script,
        )
        s.add(r)
        s.commit()
        s.refresh(r)
        pipeline_id = r.id

    msg = send_message(
        chat_id,
        f"📝 Guion propuesto #{pipeline_id} (tema: {topic['keyword']})\n\n{script}\n\n"
        f"Grabá tu voz leyendo este guion (con los ajustes que quieras) y respondé "
        f"con el audio acá mismo.",
        buttons=[[("🔄 Nuevo guion", f"regen:{pipeline_id}")]],
    )

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.status = "awaiting_audio"
        r.telegram_chat_id = chat_id
        r.telegram_script_message_id = str(msg["message_id"])
        s.commit()

    return pipeline_id


def regenerate_script(pipeline_id: int) -> None:
    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        if not r:
            return
        chat_id = r.telegram_chat_id
        keyword = (r.topic_source or "").split(":", 1)[-1] or "desarrollo personal"

    topic = pick_topic()
    script = generate_from_topic(topic)

    with SessionLocal() as s:
        r = s.get(ReelPipeline, pipeline_id)
        r.script_text = script
        r.topic_source = f"youtube_search:{topic['keyword']}"
        s.commit()

    send_message(
        chat_id,
        f"📝 Guion regenerado #{pipeline_id} (tema: {topic['keyword']})\n\n{script}\n\n"
        f"Grabá tu voz y respondé con el audio acá.",
        buttons=[[("🔄 Nuevo guion", f"regen:{pipeline_id}")]],
    )
