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
# feedback Franco: "dynamic dramatic pose" salia agresivo/de pelea - el
# personaje tiene que narrar, no combatir. Shonen narrativo: expresion calida,
# boca entreabierta como hablando, elemento distintivo propio del personaje
# (objeto/simbolo asociado) en vez de solo pose+aura generica.
SHONEN_STYLE_PREFIX = (
    "shonen anime manga illustration, digital anime art, NOT a photo, NOT a statue, "
    "NOT photorealistic, One Piece Shonen Jump narrator style, warm calm expression, "
    "mouth slightly open as if speaking to the viewer, storytelling pose, NOT a battle "
    "pose, NOT aggressive, include one distinctive object or symbol associated with the "
    "character, vibrant colors, soft glowing aura, dramatic lighting, high detail anime "
    "portrait of "
)

# feedback Franco: el txt2img puro (prompt solo con el nombre) ignoraba la
# identidad real y devolvia siempre el mismo "protagonista shonen generico"
# para cualquier autor - cero parecido, y ademas indistinguible entre
# personajes distintos. Probado img2img real (`kontext` de Pollinations)
# pero ya no es anonimo/gratis - pide cuenta en enter.pollinations.ai y no
# esta confirmado que el tier gratis alcance sin pagar (regla de Franco: cero
# tokens pagos). Fix que SI es gratis verificado: sacar rasgos fisicos reales
# de la bio de Wikipedia (via Gemini free tier, ya el unico LLM del canal) e
# inyectarlos en el prompt de texto - cada personaje sale visualmente
# distinto y mas fiel, sin transformar una foto real.
WIKI_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
TRAITS_CACHE_FILE = "traits_cache.json"


def _wikipedia_extract(vehiculo: str) -> str | None:
    """Bio corta del personaje via Wikipedia REST API (gratis, sin key).
    Prueba espanol primero, cae a ingles. None si no hay pagina (figuras muy
    oscuras/ficticias)."""
    import requests

    title = quote(vehiculo.replace(" ", "_"))
    for lang in ("es", "en"):
        try:
            url = WIKI_SUMMARY_URL.format(lang=lang, title=title)
            resp = requests.get(url, timeout=15, headers={"User-Agent": "yt-automation/1.0"})
            if resp.status_code != 200:
                continue
            extract = resp.json().get("extract")
            if extract:
                return extract
        except Exception as e:
            print(f"[vehicle_art] wikipedia lookup fallo para '{vehiculo}' ({lang}): {e}", file=sys.stderr)
    return None


def _visual_traits(vehiculo: str, root: Path) -> str:
    """Rasgos fisicos distintivos en una frase corta, cacheados en disco (1
    llamada a Gemini por vehiculo nuevo, no por video). Si Wikipedia o Gemini
    fallan, degrada a "" - el prompt sigue funcionando solo con el nombre."""
    from app.gemini import ask_text

    slug = _slug(vehiculo)
    cache_path = root / TRAITS_CACHE_FILE
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if slug in cache:
        return cache[slug]

    traits = ""
    bio = _wikipedia_extract(vehiculo)
    if bio:
        try:
            prompt = (
                f"Bio: {bio[:600]}\n\n"
                "En una frase corta (max 15 palabras, sin comillas), describe rasgos "
                "FISICOS distintivos para dibujar el personaje: edad aproximada, pelo, "
                "rostro, vestimenta/epoca tipica. Solo la frase, nada mas."
            )
            traits = ask_text(prompt).strip().strip('"')
        except Exception as e:
            print(f"[vehicle_art] gemini traits fallo para '{vehiculo}': {e}", file=sys.stderr)

    cache[slug] = traits
    root.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    return traits

_rembg_session = None


def _slug(name: str) -> str:
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


slug_for = _slug  # alias publico, usado por render_worker/telegram_webhook


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


def _fetch_candidates(vehiculo: str, out_dir: Path, k: int, root: Path) -> list[Path]:
    """Genera k variaciones (seeds distintos) en estilo shonen, con rasgos
    fisicos reales del personaje (Wikipedia+Gemini, cacheados) sumados al
    prompt para que cada figura salga distinguible y mas fiel."""
    import requests

    out_dir.mkdir(parents=True, exist_ok=True)
    traits = _visual_traits(vehiculo, root)
    suffix = f", {traits}" if traits else ""
    prompt = quote(f"{SHONEN_STYLE_PREFIX}{vehiculo}{suffix}")
    base_url = POLLINATIONS_URL.format(prompt=prompt)

    paths: list[Path] = []
    for seed in range(k):
        try:
            url = f"{base_url}?width=768&height=1024&nologo=true&seed={seed}"
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


def _generate_and_cutout(vehiculo: str, root: Path) -> list[Path]:
    """Genera N_FETCH candidatos + rembg cutout, guarda en vehiculos/<slug>/.
    No toca el estado de aprobacion - eso lo maneja el caller."""
    slug = _slug(vehiculo)
    folder = root / slug
    tmp = folder / "_tmp"
    candidates = _fetch_candidates(vehiculo, tmp, N_FETCH, root)
    if not candidates:
        return []

    manifest = _load_manifest(root)
    clips = manifest.setdefault("clips", [])
    kept: list[Path] = []
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
        kept.append(dst)

    for f in tmp.glob("*"):
        f.unlink(missing_ok=True)
    if tmp.exists() and not any(tmp.iterdir()):
        tmp.rmdir()

    _save_manifest(root, manifest)
    return kept


def _contact_sheet(paths: list[Path], dst: Path) -> Path | None:
    """Junta los cutouts lado a lado sobre fondo oscuro (fondo original es
    transparente, invisible en un jpg blanco) para mandar por Telegram como
    una sola foto de revision."""
    from PIL import Image
    imgs = []
    for p in paths:
        try:
            imgs.append(Image.open(p).convert("RGBA"))
        except Exception:
            continue
    if not imgs:
        return None
    h = 512
    resized = [im.resize((int(im.width * h / im.height), h)) for im in imgs]
    total_w = sum(im.width for im in resized) + 20 * (len(resized) - 1)
    sheet = Image.new("RGB", (total_w, h), (10, 16, 14))
    x = 0
    for im in resized:
        sheet.paste(im, (x, 0), im)
        x += im.width + 20
    dst.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dst, "JPEG", quality=90)
    return dst


def get_vehicle_art(vehiculo: str, n: int = 2) -> list[Path]:
    """SOLO devuelve arte ya aprobado por Franco (gate de calidad via
    Telegram - feedback: un personaje mal generado, una vez cacheado, se
    repite en todos los videos futuros que lo usen). Si el vehiculo es
    nuevo o esta pendiente de revision, devuelve [] - usar
    get_or_request_review() para disparar/consultar el pedido."""
    if not vehiculo:
        return []
    slug = _slug(vehiculo)
    root = VEHICLE_ROOT
    manifest = _load_manifest(root)
    if manifest.get("approvals", {}).get(slug, {}).get("status") != "approved":
        return []
    return _pick_from_cache(root, slug, n)


def get_or_request_review(vehiculo: str) -> tuple[list[Path], Path | None]:
    """Punto de entrada del render_worker antes de renderizar un segmento.
    Devuelve (arte_aprobado, None) si ya esta listo para usar. Si no,
    devuelve ([], hoja_de_contacto) la PRIMERA vez que se pide (recien
    generada, el caller debe mandarla a revision por Telegram); en pedidos
    pendientes posteriores devuelve ([], None) - no reenvia denuevo."""
    if not vehiculo:
        return [], None
    slug = _slug(vehiculo)
    root = VEHICLE_ROOT
    manifest = _load_manifest(root)
    approvals = manifest.setdefault("approvals", {})
    entry = approvals.get(slug)

    if entry and entry.get("status") == "approved":
        return _pick_from_cache(root, slug, 2), None
    if entry and entry.get("status") == "pending":
        return [], None

    candidates = _generate_and_cutout(vehiculo, root)
    if not candidates:
        return [], None
    sheet = _contact_sheet(candidates, root / slug / "review_sheet.jpg")
    if not sheet:
        return [], None
    approvals[slug] = {"status": "pending", "name": vehiculo}
    _save_manifest(root, manifest)
    return [], sheet


def approve_vehicle(slug: str) -> None:
    root = VEHICLE_ROOT
    manifest = _load_manifest(root)
    approvals = manifest.setdefault("approvals", {})
    if slug in approvals:
        approvals[slug]["status"] = "approved"
        _save_manifest(root, manifest)


def reject_vehicle(slug: str) -> str | None:
    """Borra candidatos actuales y el estado pending - la proxima
    get_or_request_review() genera de cero. Devuelve el nombre del
    vehiculo (para regenerar en el momento) o None si no habia pedido."""
    root = VEHICLE_ROOT
    manifest = _load_manifest(root)
    approvals = manifest.setdefault("approvals", {})
    entry = approvals.pop(slug, None)
    folder = root / slug
    for f in folder.glob("*.png"):
        f.unlink(missing_ok=True)
    (folder / "review_sheet.jpg").unlink(missing_ok=True)
    manifest["clips"] = [c for c in manifest.get("clips", []) if c.get("vehiculo") != slug]
    _save_manifest(root, manifest)
    return entry.get("name") if entry else None
