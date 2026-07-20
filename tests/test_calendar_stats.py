import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

TOKEN = os.getenv("API_TOKEN", "change-me-in-production")
H = {"Authorization": f"Bearer {TOKEN}"}


def test_create_post_and_stats():
    c = TestClient(app)
    # Crear video
    v = c.post("/api/videos", json={"title": "Video para stats"}, headers=H).json()
    vid = v["id"]
    # Programar post
    r = c.post("/api/posts", json={"video_id": vid, "scheduled_at": "2026-08-01T10:00:00", "platform": "youtube"}, headers=H)
    assert r.status_code == 201, r.text
    # Stats
    s = c.get("/api/stats", headers=H).json()
    assert s["total"] >= 1
    assert "by_stage" in s
    assert "upcoming" in s
    # upcoming debe incluir nuestro post
    assert any(p["video_id"] == vid for p in s["upcoming"])
