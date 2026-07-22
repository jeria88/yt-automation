"""Poller que corre en el Oracle bare host (Node+Remotion no viven en el
contenedor liviano de Coolify). Busca ReelPipeline en storyboard_ready via la
API publica, arma el arte de vehiculo + props.json, renderiza con Remotion, y
sube el mp4 de vuelta a la API. No toca content-studio ni sus servicios."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

API_BASE = os.environ.get("API_BASE", "https://yt-automation.146.181.39.4.sslip.io")
API_TOKEN = os.environ["API_TOKEN"]
REMOTION_DIR = Path(os.environ.get("REMOTION_DIR", "/home/ubuntu/yt-automation-render/remotion"))
PUBLIC_DIR = REMOTION_DIR / "public"
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "30"))

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.vehicle_art import get_vehicle_art  # noqa: E402

H = {"Authorization": f"Bearer {API_TOKEN}"}


def _patch(pipeline_id: int, status: str, last_error: str | None = None) -> None:
    body = {"status": status}
    if last_error is not None:
        body["last_error"] = last_error
    requests.patch(f"{API_BASE}/api/reel-pipeline/{pipeline_id}", json=body, headers=H, timeout=30)


def _fetch_pending() -> list[dict]:
    resp = requests.get(f"{API_BASE}/api/reel-pipeline", params={"status": "storyboard_ready"}, headers=H, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _download_audio(pipeline_id: int, dst: Path) -> None:
    resp = requests.get(f"{API_BASE}/api/reel-pipeline/{pipeline_id}/audio", headers=H, timeout=60)
    resp.raise_for_status()
    dst.write_bytes(resp.content)


def _build_props(pipeline: dict, audio_filename: str) -> dict:
    storyboard = json.loads(pipeline["storyboard_json"])
    segments = []
    for i, seg in enumerate(storyboard["segments"]):
        art_filename = None
        paths = get_vehicle_art(seg["vehiculo"], n=1)
        if paths:
            art_filename = f"seg{i}.png"
            (PUBLIC_DIR / art_filename).write_bytes(Path(paths[0]).read_bytes())
        segments.append({
            "start": seg["start"], "end": seg["end"],
            "vehiculoArt": art_filename, "transitionIn": seg.get("transition_in", "cut"),
        })

    hook = (pipeline.get("script_text") or "").split("HOOK:")[-1].split("PROBLEMA:")[0].strip()
    cta = (pipeline.get("script_text") or "").split("CTA:")[-1].strip()

    return {
        "texts": {"hook": hook[:200], "cta": cta[:200] or "Suscribite para el viaje interior"},
        "tokens": {"jade": "#7ecfa8", "cream": "#F0E8DC", "dark": "#040810"},
        "domain": "ReyPirataChaman",
        "narrationAudio": audio_filename,
        "durationSeconds": storyboard["audio_duration_seconds"],
        "segments": segments,
    }


def _render(pipeline_id: int, props: dict) -> Path:
    props_path = REMOTION_DIR / f"props_{pipeline_id}.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False))
    out_path = Path(f"/tmp/elenco_{pipeline_id}.mp4")
    subprocess.run(
        ["npx", "remotion", "render", "elenco", str(out_path), f"--props={props_path}", "--concurrency=2"],
        cwd=REMOTION_DIR, check=True, timeout=1800,
    )
    return out_path


def process_one(pipeline: dict) -> None:
    pipeline_id = pipeline["id"]
    print(f"[render_worker] procesando pipeline {pipeline_id}")
    _patch(pipeline_id, "rendering")
    try:
        audio_filename = f"narration_{pipeline_id}.ogg"
        _download_audio(pipeline_id, PUBLIC_DIR / audio_filename)
        props = _build_props(pipeline, audio_filename)
        mp4_path = _render(pipeline_id, props)
        with open(mp4_path, "rb") as f:
            resp = requests.post(
                f"{API_BASE}/api/reel-pipeline/{pipeline_id}/render-complete",
                files={"file": (f"{pipeline_id}.mp4", f, "video/mp4")},
                headers=H, timeout=300,
            )
            resp.raise_for_status()
        mp4_path.unlink(missing_ok=True)
        print(f"[render_worker] pipeline {pipeline_id} -> render_ready")
    except Exception as e:
        print(f"[render_worker] pipeline {pipeline_id} fallo: {e}")
        _patch(pipeline_id, "error", last_error=f"render: {e}")


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[render_worker] arrancando, poll cada {POLL_SECONDS}s")
    while True:
        try:
            pending = _fetch_pending()
            for pipeline in pending:
                process_one(pipeline)
        except Exception as e:
            print(f"[render_worker] error en el loop: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
