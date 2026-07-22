"""Genera titulo + descripcion para YouTube a partir del guion, via Gemini
(mismo proveedor free-tier del resto del pipeline)."""
from app.gemini import ask_json

PROMPT = """Sos experto en YouTube growth. Te doy un guion de un video corto
(formato HOOK/PROBLEMA/AGITAR/SOLUCION/CTA) de un canal de desarrollo personal,
conciencia y meditacion llamado "ReyPirataChaman". Genera:
- Un TITULO de YouTube (maximo 90 caracteres) que funcione como gancho fuerte,
  sin clickbait vacio, fiel al contenido.
- Una DESCRIPCION de YouTube (200-400 caracteres) con un resumen + 3-5 hashtags
  del nicho (conciencia, meditacion, desarrollo personal, viaje interior).

Guion:
{script}

Devolveme SOLO JSON: {{"title": "...", "description": "..."}}
"""


def generate_metadata(script_text: str) -> dict:
    return ask_json(PROMPT.format(script=script_text))
