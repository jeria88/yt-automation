import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

def test_unauthorized_without_token():
    client = TestClient(app)
    r = client.get("/api/videos")
    assert r.status_code == 401

def test_authorized_with_token():
    client = TestClient(app)
    token = os.getenv("API_TOKEN", "change-me-in-production")
    r = client.get("/api/videos", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
