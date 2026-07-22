import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pytest

from app import gemini


class _FakeResp:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=self)

    def json(self):
        return self._json


def test_retries_on_503_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setattr(gemini.time, "sleep", lambda *a: None)

    calls = {"n": 0}

    def fake_post(url, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            return _FakeResp(503)
        return _FakeResp(200, {"candidates": [{"content": {"parts": [{"text": "listo"}]}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    assert gemini.ask_text("hola") == "listo"
    assert calls["n"] == 3


def test_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setattr(gemini.time, "sleep", lambda *a: None)
    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: _FakeResp(503))

    with pytest.raises(httpx.HTTPStatusError):
        gemini.ask_text("hola")


def test_does_not_retry_on_4xx_client_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    calls = {"n": 0}

    def fake_post(url, **kwargs):
        calls["n"] += 1
        return _FakeResp(400)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        gemini.ask_text("hola")
    assert calls["n"] == 1
