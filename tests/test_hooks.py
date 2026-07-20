import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

TOKEN = os.getenv("API_TOKEN", "change-me-in-production")
H = {"Authorization": f"Bearer {TOKEN}"}


def test_create_hook():
    c = TestClient(app)
    r = c.post("/api/hooks", json={"text": "Gancho de prueba", "source": "manual", "tags": "motivacion"}, headers=H)
    assert r.status_code == 201, r.text
    assert r.json()["text"] == "Gancho de prueba"


def test_filter_by_source():
    c = TestClient(app)
    c.post("/api/hooks", json={"text": "reddit hook", "source": "reddit"}, headers=H)
    r = c.get("/api/hooks?source=reddit", headers=H)
    assert r.status_code == 200
    assert all(h["source"] == "reddit" for h in r.json())


def test_reddit_fetch_fallback_or_real():
    # No debe romper si no hay creds de Reddit: devuelve lista (mock o real)
    c = TestClient(app)
    r = c.get("/api/hooks/reddit?query=motivacion&limit=2", headers=H)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
