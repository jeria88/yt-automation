"""Transcribe el audio real de Franco y arma el storyboard multi-vehiculo.
Portado del spike validado (Fase 0/3 del plan) - whisper + Gemini, sin
dependencia de content-studio en runtime."""
import os

from app.gemini import ask_json

WHISPER_CACHE_DIR = os.getenv("WHISPER_CACHE_DIR", "./whisper_cache")

PROMPT = """Sos un editor de video. Te doy un guion narrado y sus segmentos con
timestamps reales (de una transcripcion de audio). Tu trabajo es dividir el guion
en 2 a 4 "beats" narrativos, y para cada uno asignar un vehiculo.

REGLA DURA: "vehiculo" tiene que ser el NOMBRE PROPIO de una persona o personaje
real e identificable (historica, publica, celebridad, o de ficcion reconocible) -
alguien de quien existan fotos o imagenes buscables en internet. NUNCA una frase
abstracta, un concepto, ni una descripcion (mal: "la ansiedad inexplicable",
"el cuerpo como memoria" - bien: "Carl Jung", "Eckhart Tolle", "Bruce Lee").
Si el guion no menciona a nadie explicito, elegi vos la figura real mas asociada
al tema de ese beat (un pensador, cientifico, monje, artista, etc. conocido por
ese tema) - nunca inventes una etiqueta conceptual en su lugar.
Un mismo vehiculo puede repetirse en mas de un beat si tiene sentido narrativo,
pero si el guion tiene temas claramente distintos, preferi variar el vehiculo
entre beats para que la pieza transite entre mas de un personaje.

Guion completo:
{script}

Segmentos con timestamps (inicio-fin en segundos, texto):
{segments}

Ademas, para cada beat asigna un "broll_keyword": 1-3 palabras EN INGLES que
describan el tema/mood visual de ese beat para buscar un GIF de fondo (ej.
"ocean waves", "cosmic space", "deep breathing", "mirror reflection") - nunca
el nombre del vehiculo, es sobre el TEMA que se esta narrando en ese momento.

Y una "quote": una cita corta (maximo 140 caracteres) atribuible al vehiculo
de ese beat, relacionada con lo que se esta narrando en ese momento - preferi
una cita REAL y conocida de esa persona si existe y calza con el tema; si no,
una frase breve coherente con su forma de pensar (nunca inventes una cita
absurda o que contradiga lo que esa persona realmente defendia). En espanol.

Devolveme SOLO un JSON con esta forma exacta, sin texto extra:
{{
  "segments": [
    {{"index": 0, "start": 0.0, "end": 12.3, "vehiculo": "Nombre Real Y Apellido", "broll_keyword": "ocean waves", "quote": "Cita corta y relevante.", "transition_in": "cut"}},
    ...
  ]
}}
transition_in debe ser "cut" para el primer segmento y "xfade" o "cut" para el resto.
"""

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("small", device="cpu", compute_type="int8", download_root=WHISPER_CACHE_DIR)
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Con word_timestamps=True: cada segmento trae tambien sus palabras con
    start/end reales, para subtitulos karaoke (feedback Franco: sin esto el
    video se siente sin ritmo, nada llama la atencion cada pocos segundos)."""
    segments, _ = _get_model().transcribe(audio_path, word_timestamps=True, language="es")
    out = []
    for s in segments:
        words = [{"word": w.word.strip(), "start": w.start, "end": w.end} for w in (s.words or [])]
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(), "words": words})
    return out


def build_storyboard(script: str, audio_path: str) -> dict:
    segments = transcribe(audio_path)
    seg_text = "\n".join(f"{s['start']:.1f}-{s['end']:.1f}: {s['text']}" for s in segments)
    storyboard = ask_json(PROMPT.format(script=script, segments=seg_text))
    storyboard["audio_duration_seconds"] = segments[-1]["end"] if segments else 0.0
    storyboard["transcript"] = segments
    return storyboard
