import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.db import SessionLocal, Script, Video
from app.auth import get_current_token
from app.prompts.hormozi import build_skeleton, build_llm_prompt, PHILOSOPHIES

router = APIRouter(prefix="/api/scripts", dependencies=[Depends(get_current_token)])


class ScriptIn(BaseModel):
    hook: str
    philosophy: str = "espejo"  # espejo, sombra, pilares
    video_id: int | None = None


def generate(hook: str, philosophy: str) -> str:
    key = os.getenv("OPENROUTER_KEY")
    if not key:
        return build_skeleton(hook, philosophy)
    try:
        return _call_openrouter(hook, philosophy)
    except Exception:
        return build_skeleton(hook, philosophy)


def _call_openrouter(hook: str, philosophy: str) -> str:
    key = os.getenv("OPENROUTER_KEY")
    model = os.getenv("OPENROUTER_MODEL", "tencent/hy3:free")
    system = (
        "Eres guionista de YouTube faceless, desarrollo personal. Estructura Hormozi EXACTA "
        "usando estos 5 encabezados en mayúsculas, cada uno en su propia línea: "
        "HOOK:, PROBLEMA:, AGITAR:, SOLUCION:, CTA:. Español neutro, sin voseo. "
        "Integra la filosofía Endonautas como trasfondo. Máximo 250 palabras."
    )
    phil = PHILOSOPHIES.get(philosophy, PHILOSOPHIES["espejo"])
    user = f"Gancho: {hook}\nFilosofía: {phil}\nGenera el guion con los 5 encabezados."
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 600,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


@router.post("", status_code=201)
def create_script(payload: ScriptIn):
    body = generate(payload.hook, payload.philosophy)
    with SessionLocal() as s:
        sc = Script(body=body, philosophy=payload.philosophy, video_id=payload.video_id)
        s.add(sc)
        s.commit()
        s.refresh(sc)
        return {"id": sc.id, "body": sc.body, "philosophy": sc.philosophy}
