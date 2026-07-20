import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

TOKEN = os.getenv("API_TOKEN", "change-me-in-production")
H = {"Authorization": f"Bearer {TOKEN}"}

def _client():
    return TestClient(app)

def test_create_video():
    c = _client()
    r = c.post("/api/videos", json={"title": "Video prueba", "stage": "idea"}, headers=H)
    assert r.status_code == 201, r.text
    assert r.json()["title"] == "Video prueba"

def test_list_videos():
    c = _client()
    r = c.get("/api/videos", headers=H)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_stage():
    c = _client()
    created = c.post("/api/videos", json={"title": "Mover etapa"}, headers=H).json()
    vid = created["id"]
    r = c.patch(f"/api/videos/{vid}", json={"stage": "guion"}, headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "guion"

def test_invalid_stage_rejected():
    c = _client()
    r = c.post("/api/videos", json={"title": "x", "stage": "noexiste"}, headers=H)
    assert r.status_code == 422
