import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

TOKEN = os.getenv("API_TOKEN", "change-me-in-production")
H = {"Authorization": f"Bearer {TOKEN}"}

SECTIONS = ["hook", "problema", "agitar", "solucion", "cta"]


def test_generate_has_5_sections():
    c = TestClient(app)
    r = c.post("/api/scripts", json={"hook": "El tiempo es una ilusión", "philosophy": "espejo"}, headers=H)
    assert r.status_code == 201, r.text
    body = r.json()["body"]
    for sec in SECTIONS:
        assert sec in body.lower(), f"falta seccion {sec}"


def test_generate_without_llm_returns_skeleton():
    # Sin OPENROUTER_KEY el generador debe devolver esqueleto (no romper)
    c = TestClient(app)
    r = c.post("/api/scripts", json={"hook": "x", "philosophy": "sombra"}, headers=H)
    assert r.status_code == 201
    assert "solucion" in r.json()["body"].lower()
