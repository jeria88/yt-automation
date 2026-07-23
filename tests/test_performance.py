import datetime
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal, ReelPipeline, VideoMetrics
import app.pipeline_jobs as pipeline_jobs
from app.performance_learnings import top_performers


def _make_published(monkeypatch, hours_ago, views, hook_variant=1):
    with SessionLocal() as s:
        row = ReelPipeline(
            status="published", telegram_chat_id="555", script_text="x",
            rendered_video_path="x.mp4", youtube_video_id="abc123", hook_variant=hook_variant,
            updated_at=datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago),
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        pid = row.id
    monkeypatch.setattr(pipeline_jobs, "save_snapshot", lambda pipeline_id, video_id: {"views": views, "likes": 0})
    return pid


def test_too_soon_does_not_check(monkeypatch):
    pid = _make_published(monkeypatch, hours_ago=1, views=0)
    result = pipeline_jobs.check_performance_and_regen(pid)
    assert result == "too_soon"


def test_good_performance_marks_monitoring(monkeypatch):
    monkeypatch.setattr(pipeline_jobs, "send_message", lambda *a, **kw: None)
    pid = _make_published(monkeypatch, hours_ago=49, views=100)
    result = pipeline_jobs.check_performance_and_regen(pid)
    assert result == "kept"
    with SessionLocal() as s:
        assert s.get(ReelPipeline, pid).status == "monitoring"


def test_underperformance_triggers_regen(monkeypatch):
    sent = []
    monkeypatch.setattr(pipeline_jobs, "send_message", lambda chat_id, text, **kw: sent.append(text))
    monkeypatch.setattr(pipeline_jobs, "regenerate_and_update", lambda *a, **kw: {"title": "Nuevo Titulo", "description": "d"})
    pid = _make_published(monkeypatch, hours_ago=49, views=1)

    result = pipeline_jobs.check_performance_and_regen(pid)

    assert result == "regenerated"
    with SessionLocal() as s:
        row = s.get(ReelPipeline, pid)
        assert row.status == "monitoring"
        assert row.title == "Nuevo Titulo"
        assert row.hook_variant == 2
    assert any("Nuevo Titulo" in s_ for s_ in sent)


def test_underperformance_but_already_regenerated_max_times_keeps(monkeypatch):
    monkeypatch.setattr(pipeline_jobs, "send_message", lambda *a, **kw: None)
    pid = _make_published(monkeypatch, hours_ago=49, views=1, hook_variant=2)  # ya regenero 1 vez (MAX=1)
    result = pipeline_jobs.check_performance_and_regen(pid)
    assert result == "kept"


def test_top_performers_orders_by_views():
    with SessionLocal() as s:
        s.query(VideoMetrics).delete()
        s.query(ReelPipeline).delete()
        s.commit()
        low = ReelPipeline(status="published", title="Bajo", script_text="x")
        high = ReelPipeline(status="monitoring", title="Alto", script_text="x")
        s.add_all([low, high])
        s.commit()
        s.refresh(low)
        s.refresh(high)
        s.add_all([
            VideoMetrics(reel_pipeline_id=low.id, views=5),
            VideoMetrics(reel_pipeline_id=high.id, views=500),
        ])
        s.commit()

    top = top_performers(limit=5)
    assert top[0]["title"] == "Alto"
