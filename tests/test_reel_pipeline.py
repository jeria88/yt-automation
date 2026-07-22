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
