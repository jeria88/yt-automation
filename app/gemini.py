"""Wrapper minimo sobre Gemini free tier. Unico proveedor de LLM del pipeline
ReyPirataChaman (decision explicita de Franco: cero tokens pagos, ni baratos)."""
import json
import os
import time

import httpx

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# ponytail: free tier de Gemini devuelve 429/503 seguido bajo carga y el
# rate-limit tarda mas que unos segundos en liberarse (visto en produccion:
# 3 intentos con 3-12s no alcanzaba, seguia 429). 5 intentos con backoff
# 5/10/20/40s (75s de margen total) le da tiempo real a que se libere.
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 5


def _post_with_retry(payload: dict) -> dict:
    key = os.environ["GEMINI_API_KEY"]
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(f"{GEMINI_URL}?key={key}", json=payload, timeout=60)
            if resp.status_code in RETRY_STATUSES and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt * BACKOFF_BASE_SECONDS)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code not in RETRY_STATUSES or attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt * BACKOFF_BASE_SECONDS)
    raise last_error


def ask_json(prompt: str) -> dict:
    data = _post_with_retry({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"},
    })
    content = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(content)


def ask_text(prompt: str) -> str:
    data = _post_with_retry({"contents": [{"parts": [{"text": prompt}]}]})
    return data["candidates"][0]["content"]["parts"][0]["text"]
