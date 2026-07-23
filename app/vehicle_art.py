"""Arte por vehiculo: cutouts PNG transparentes de la figura real que narra
cada segmento del storyboard, generados en estilo shonen anime consistente
(feedback Franco: el estilo mixto de fotos/ilustraciones scrapeadas de
internet no le gustaba - quiere el mismo estilo del logo del canal, un
personaje/aura estilo One Piece, aplicado a cada figura real).

Generacion via Pollinations.ai (gratis, sin API key, sin login - genera con
Flux/SDXL via un simple GET) en vez de buscar imagenes existentes. + recorte
(rembg, gratis) + cache en disco. Sin gate VLM (v1: content-studio lo salta
igual sin key VLM dedicada; aca directamente no lo implementamos todavia,
ver Fase 4 notas)."""
import io
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

VEHICLE_ROOT = Path(os.getenv("VEHICLE_ART_DIR", "./vehiculos"))
REMBG_CACHE_DIR = os.getenv("REMBG_CACHE_DIR", "./rembg_cache")
N_FETCH = int(os.getenv("VEHICLE_N_FETCH", "3"))
MIN_SUBJECT_PX = int(os.getenv("VEHICLE_MIN_SUBJECT_PX", "600"))

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
# Estilo primero y repetido - el modelo pesa fuerte los primeros tokens, y
# nombres muy asociados a una estatua/pintura especifica (ej. "Marcus
# Aurelius") pueden pisar el prompt de estilo si no se insiste (probado:
# seed 0 devolvio una estatua de bronce en vez de anime, seed 1 SI dio anime).
SHONEN_STYLE_PREFIX = (
    "shonen anime manga illustration, digital anime art, NOT a photo, NOT a statue, "
    "NOT photorealistic, One Piece Shonen Jump style, vibrant colors, dynamic dramatic pose, "
    "glowing aura effect, dramatic lighting, high detail anime portrait of "
)

_rembg_session = None


def _slug(name: str) -> str:
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _load_manifest(root: Path) -> dict:
    path = root / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"clips": []}


def _save_manifest(root: Path, manifest: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _subject_height_px(png: Path) -> int:
    from PIL import Image
    try:
        img = Image.open(png).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        return 0 if not bbox else bbox[3] - bbox[1]
    except Exception:
        return 0


def _pick_from_cache(root: Path, slug: str, n: int) -> list[Path]:
    folder = root / slug
    files = sorted(folder.glob("*.png"))
    if not files:
        return []
    meta = {c["file"]: c for c in _load_manifest(root).get("clips", []) if c.get("vehiculo") == slug}
    kept = []
    for p in files:
        m = meta.get(f"{slug}/{p.name}", {})
        if m.get("exclude"):
            continue
        if _subject_height_px(p) < MIN_SUBJECT_PX:
            continue
        kept.append((m.get("score", 0), p))
    kept.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in kept][:n]


def _fetch_candidates(vehiculo: str, out_dir: Path, k: int) -> list[Path]:
    """Genera k variaciones (seeds distintos) en estilo shonen, en vez de
    buscar imagenes existentes - eso era lo que daba el estilo inconsistente
    que Franco no queria."""
    import requests

    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = quote(f"{SHONEN_STYLE_PREFIX}{vehiculo}")
    paths: list[Path] = []
    for seed in range(k):
        try:
            url = f"{POLLINATIONS_URL.format(prompt=prompt)}?width=768&height=1024&nologo=true&seed={seed}"
            data = requests.get(url, timeout=60).content
            dst = out_dir / f"cand-{seed:02d}.jpg"
            dst.write_bytes(data)
            paths.append(dst)
        except Exception as e:
            print(f"[vehicle_art] generacion fallo para '{vehiculo}' seed {seed}: {e}", file=sys.stderr)
    return paths


def _cutout(src: Path, dst: Path) -> bool:
    global _rembg_session
    from PIL import Image
    try:
        Image.open(src)
    except Exception:
        return False
    try:
        from rembg import new_session, remove
        if _rembg_session is None:
            os.environ.setdefault("U2NET_HOME", REMBG_CACHE_DIR)
            # isnet-anime (no u2net generico): mismo modelo que usa content-studio
            # para arte estilo anime - u2net dejaba halos blancos difusos en el
            # aura/pelo de las imagenes generadas en estilo shonen.
            _rembg_session = new_session("isnet-anime")
        out = remove(src.read_bytes(), session=_rembg_session)
        Image.open(io.BytesIO(out)).convert("RGBA").save(dst, "PNG")
        return True
    except Exception as e:
        print(f"[vehicle_art] rembg fallo en {src.name}: {e}", file=sys.stderr)
        return False


def get_vehicle_art(vehiculo: str, n: int = 2) -> list[Path]:
    """n cutouts PNG del vehiculo, mejores primero. Cache primero, fetch
    on-demand si hace falta. [] si no se consigue nada usable (el caller
    degrada: sin capa de personaje para ese segmento)."""
    if not vehiculo:
        return []
    slug = _slug(vehiculo)
    root = VEHICLE_ROOT

    cached = _pick_from_cache(root, slug, n)
    if len(cached) >= n:
        return cached

    folder = root / slug
    tmp = folder / "_tmp"
    candidates = _fetch_candidates(vehiculo, tmp, N_FETCH)
    if not candidates:
        return cached

    manifest = _load_manifest(root)
    clips = manifest.setdefault("clips", [])
    for i, src in enumerate(candidates):
        dst = folder / f"{slug}-{i:02d}.png"
        if not _cutout(src, dst):
            continue
        if _subject_height_px(dst) < MIN_SUBJECT_PX:
            dst.unlink(missing_ok=True)
            continue
        rel = f"{slug}/{dst.name}"
        clips[:] = [c for c in clips if c.get("file") != rel]
        clips.append({"file": rel, "vehiculo": slug, "score": 50})

    for f in tmp.glob("*"):
        f.unlink(missing_ok=True)
    if tmp.exists() and not any(tmp.iterdir()):
        tmp.rmdir()

    _save_manifest(root, manifest)
    return _pick_from_cache(root, slug, n)
