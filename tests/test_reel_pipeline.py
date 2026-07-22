import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, ReelPipeline

TOKEN = os.getenv("API_TOKEN", "change-me-in-production")
H = {"Authorization": f"Bearer {TOKEN}"}


class _FakeResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def _patch_externals(monkeypatch):
    import httpx

    def fake_get(url, **kwargs):
        if "youtube/v3/search" in url:
            return _FakeResp({"items": [{"snippet": {"title": "video de referencia", "description": "d"}}]})
        raise AssertionError(f"GET no mockeado: {url}")

    def fake_post(url, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            return _FakeResp({"candidates": [{"content": {"parts": [{"text": "HOOK:\nx\nPROBLEMA:\nx\nAGITAR:\nx\nSOLUCION:\nx\nCTA:\nx"}]}}]})
        if "api.telegram.org" in url:
            return _FakeResp({"result": {"message_id": 123}})
        raise AssertionError(f"POST no mockeado: {url}")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("YOUTUBE_API_KEY", "fake")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN_RPC", "fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID_RPC", "12345")
    monkeypatch.setenv("BACKLOG_MIN_PENDING", "1")


def test_fill_backlog_creates_pending_entry(monkeypatch):
    _patch_externals(monkeypatch)
    with SessionLocal() as s:
        s.query(ReelPipeline).delete()
        s.commit()
    c = TestClient(app)
    r = c.post("/api/reel-pipeline/fill-backlog", headers=H)
    assert r.status_code == 200, r.text
    created = r.json()["created"]
    assert len(created) >= 1

    with SessionLocal() as s:
        row = s.get(ReelPipeline, created[0])
        assert row.status == "awaiting_audio"
        assert row.script_text is not None
        assert row.telegram_chat_id == "12345"


def test_webhook_voice_updates_status(monkeypatch):
    _patch_externals(monkeypatch)
    with SessionLocal() as s:
        row = ReelPipeline(status="awaiting_audio", telegram_chat_id="999")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    import httpx

    def fake_get_with_file(url, **kwargs):
        if "getFile" in url:
            return _FakeResp({"result": {"file_path": "voice/x.oga"}})
        return _FakeResp({"items": []})

    monkeypatch.setattr(httpx, "get", fake_get_with_file)

    def fake_stream(method, url, **kwargs):
        class _S:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def raise_for_status(self_inner):
                pass

            def iter_bytes(self_inner):
                return iter([b"fake-audio-bytes"])

        return _S()

    monkeypatch.setattr(httpx, "stream", fake_stream)

    import app.routers.telegram_webhook as webhook_module
    monkeypatch.setattr(webhook_module, "process_audio", lambda pipeline_id: None)

    c = TestClient(app)
    r = c.post("/telegram/webhook", json={
        "message": {"chat": {"id": 999}, "voice": {"file_id": "abc", "duration": 30}}
    })
    assert r.status_code == 200

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.status == "audio_received"
        assert row.audio_file_path is not None
        assert row.audio_duration_seconds == 30


def _mock_voice_download(monkeypatch):
    import httpx

    def fake_get_with_file(url, **kwargs):
        if "getFile" in url:
            return _FakeResp({"result": {"file_path": "voice/x.oga"}})
        return _FakeResp({"items": []})

    def fake_stream(method, url, **kwargs):
        class _S:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def raise_for_status(self_inner):
                pass

            def iter_bytes(self_inner):
                return iter([b"fake-audio-bytes"])

        return _S()

    monkeypatch.setattr(httpx, "get", fake_get_with_file)
    monkeypatch.setattr(httpx, "stream", fake_stream)

    import app.routers.telegram_webhook as webhook_module
    monkeypatch.setattr(webhook_module, "process_audio", lambda pipeline_id: None)


def test_webhook_voice_with_caption_picks_explicit_pipeline_not_most_recent(monkeypatch):
    _patch_externals(monkeypatch)
    _mock_voice_download(monkeypatch)

    with SessionLocal() as s:
        older = ReelPipeline(status="awaiting_audio", telegram_chat_id="777")
        s.add(older)
        s.commit()
        s.refresh(older)
        older_id = older.id

        newer = ReelPipeline(status="awaiting_audio", telegram_chat_id="777")
        s.add(newer)
        s.commit()
        s.refresh(newer)
        newer_id = newer.id

    c = TestClient(app)
    # manda el audio con el numero del guion VIEJO como caption -> debe actualizar
    # el viejo, no el mas reciente (que seria el default sin caption)
    r = c.post("/telegram/webhook", json={
        "message": {
            "chat": {"id": 777},
            "audio": {"file_id": "abc", "duration": 20},
            "caption": f"guion {older_id}",
        }
    })
    assert r.status_code == 200

    with SessionLocal() as s:
        assert s.get(ReelPipeline, older_id).status == "audio_received"
        assert s.get(ReelPipeline, newer_id).status == "awaiting_audio"


def test_process_audio_builds_storyboard_and_notifies(monkeypatch):
    import app.pipeline_jobs as pipeline_jobs

    sent = []
    monkeypatch.setattr(pipeline_jobs, "send_message", lambda chat_id, text, **kw: sent.append((chat_id, text)))
    monkeypatch.setattr(pipeline_jobs, "build_storyboard", lambda script, audio_path: {
        "segments": [{"index": 0, "start": 0.0, "end": 5.0, "vehiculo": "Carl Jung", "transition_in": "cut"}],
        "audio_duration_seconds": 5.0,
    })

    with SessionLocal() as s:
        row = ReelPipeline(status="audio_received", telegram_chat_id="555", script_text="x", audio_file_path="x.ogg")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    pipeline_jobs.process_audio(pipeline_id)

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.status == "storyboard_ready"
        assert "Carl Jung" in row.storyboard_json

    assert len(sent) == 1
    assert "Carl Jung" in sent[0][1]


def test_process_audio_marks_error_on_failure(monkeypatch):
    import app.pipeline_jobs as pipeline_jobs

    monkeypatch.setattr(pipeline_jobs, "send_message", lambda *a, **kw: None)

    def boom(script, audio_path):
        raise RuntimeError("whisper reventó")

    monkeypatch.setattr(pipeline_jobs, "build_storyboard", boom)

    with SessionLocal() as s:
        row = ReelPipeline(status="audio_received", telegram_chat_id="555", script_text="x", audio_file_path="x.ogg")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    pipeline_jobs.process_audio(pipeline_id)

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.status == "error"
        assert "whisper reventó" in row.last_error


def test_audio_endpoint_serves_file(tmp_path):
    audio_file = tmp_path / "test.ogg"
    audio_file.write_bytes(b"fake-audio-bytes")

    with SessionLocal() as s:
        row = ReelPipeline(status="audio_received", audio_file_path=str(audio_file))
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    c = TestClient(app)
    r = c.get(f"/api/reel-pipeline/{pipeline_id}/audio", headers=H)
    assert r.status_code == 200
    assert r.content == b"fake-audio-bytes"


def test_audio_endpoint_404_when_missing():
    with SessionLocal() as s:
        row = ReelPipeline(status="topic_pending")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    c = TestClient(app)
    r = c.get(f"/api/reel-pipeline/{pipeline_id}/audio", headers=H)
    assert r.status_code == 404


def test_render_complete_saves_file_and_updates_status(monkeypatch):
    import app.routers.reel_pipeline as reel_pipeline_module
    monkeypatch.setattr(reel_pipeline_module, "publish_pipeline", lambda pipeline_id: None)

    with SessionLocal() as s:
        row = ReelPipeline(status="rendering")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    c = TestClient(app)
    r = c.post(
        f"/api/reel-pipeline/{pipeline_id}/render-complete",
        headers=H,
        files={"file": ("out.mp4", b"fake-mp4-bytes", "video/mp4")},
    )
    assert r.status_code == 200, r.text

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.status == "render_ready"
        assert row.rendered_video_path is not None
        assert os.path.exists(row.rendered_video_path)


def test_render_complete_saves_thumbnail(monkeypatch):
    import app.routers.reel_pipeline as reel_pipeline_module
    monkeypatch.setattr(reel_pipeline_module, "publish_pipeline", lambda pipeline_id: None)

    with SessionLocal() as s:
        row = ReelPipeline(status="rendering")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    c = TestClient(app)
    r = c.post(
        f"/api/reel-pipeline/{pipeline_id}/render-complete",
        headers=H,
        files={
            "file": ("out.mp4", b"fake-mp4-bytes", "video/mp4"),
            "thumbnail": ("thumb.jpg", b"fake-jpg-bytes", "image/jpeg"),
        },
    )
    assert r.status_code == 200, r.text

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.thumbnail_path is not None
        assert os.path.exists(row.thumbnail_path)


def test_publish_pipeline_success(monkeypatch):
    import app.pipeline_jobs as pipeline_jobs

    sent = []
    monkeypatch.setattr(pipeline_jobs, "send_message", lambda chat_id, text, **kw: sent.append(text))
    monkeypatch.setattr(pipeline_jobs, "generate_metadata", lambda script: {"title": "T", "description": "D"})
    monkeypatch.setattr(pipeline_jobs, "publish", lambda *a, **kw: {"video_id": "abc123", "url": "https://youtube.com/watch?v=abc123"})

    with SessionLocal() as s:
        row = ReelPipeline(status="render_ready", telegram_chat_id="555", script_text="x", rendered_video_path="x.mp4")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    pipeline_jobs.publish_pipeline(pipeline_id)

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.status == "published"
        assert row.youtube_video_id == "abc123"
        assert row.title == "T"
    assert any("abc123" in s or "youtube.com" in s for s in sent)


def test_publish_pipeline_marks_error_on_failure(monkeypatch):
    import app.pipeline_jobs as pipeline_jobs

    monkeypatch.setattr(pipeline_jobs, "send_message", lambda *a, **kw: None)
    monkeypatch.setattr(pipeline_jobs, "generate_metadata", lambda script: {"title": "T", "description": "D"})

    def boom(*a, **kw):
        raise RuntimeError("youtube api reventó")

    monkeypatch.setattr(pipeline_jobs, "publish", boom)

    with SessionLocal() as s:
        row = ReelPipeline(status="render_ready", script_text="x", rendered_video_path="x.mp4")
        s.add(row)
        s.commit()
        s.refresh(row)
        pipeline_id = row.id

    pipeline_jobs.publish_pipeline(pipeline_id)

    with SessionLocal() as s:
        row = s.get(ReelPipeline, pipeline_id)
        assert row.status == "error"
        assert "youtube api reventó" in row.last_error
