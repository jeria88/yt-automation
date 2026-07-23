"""Aprendizaje acumulado: que titulos/temas funcionaron mejor, para sesgar los
proximos guiones/titulos generados. Se degrada bien sin datos (canal nuevo)."""
from sqlalchemy import desc

from app.db import SessionLocal, ReelPipeline, VideoMetrics


def top_performers(limit: int = 5) -> list[dict]:
    """Ultimo snapshot de views por pipeline publicado, ordenado desc."""
    with SessionLocal() as s:
        rows = (
            s.query(ReelPipeline, VideoMetrics)
            .join(VideoMetrics, VideoMetrics.reel_pipeline_id == ReelPipeline.id)
            .filter(ReelPipeline.status.in_(["published", "monitoring"]))
            .order_by(desc(VideoMetrics.views))
            .limit(limit * 3)
            .all()
        )
    seen, out = set(), []
    for pipeline, metric in rows:
        if pipeline.id in seen:
            continue
        seen.add(pipeline.id)
        out.append({"title": pipeline.title, "topic_source": pipeline.topic_source, "views": metric.views})
        if len(out) >= limit:
            break
    return out


def learnings_prompt_context() -> str:
    """Texto para inyectar en prompts de generacion. Vacio si no hay datos todavia."""
    top = top_performers()
    if not top:
        return ""
    lines = "\n".join(f"- \"{t['title']}\" ({t['views']} vistas)" for t in top if t["title"])
    if not lines:
        return ""
    return (
        "\n\nTitulos que mejor funcionaron en el canal hasta ahora (usalos como referencia "
        f"de angulo/tono, no los copies literal):\n{lines}\n"
    )
