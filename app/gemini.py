"""Wrapper minimo sobre Gemini free tier. Unico proveedor de LLM del pipeline
ReyPirataChaman (decision explicita de Franco: cero tokens pagos, ni baratos)."""
import json
import os

import httpx

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def ask_json(prompt: str) -> dict:
    key = os.environ["GEMINI_API_KEY"]
    resp = httpx.post(
        f"{GEMINI_URL}?key={key}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(content)


def ask_text(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    resp = httpx.post(
        f"{GEMINI_URL}?key={key}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
