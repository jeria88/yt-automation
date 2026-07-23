"""Genera un guion propuesto a partir de una tematica del nicho, via Gemini.
Reusa la estructura Hormozi + filosofia Endonautas ya definida en prompts/hormozi.py."""
import random

from app.gemini import ask_text
from app.prompts.hormozi import PHILOSOPHIES

SYSTEM = (
    "Eres guionista de YouTube faceless, canal de desarrollo personal / conciencia / "
    "meditacion / viaje interior. Estructura Hormozi EXACTA usando estos 5 encabezados "
    "en mayusculas, cada uno en su propia linea: HOOK:, PROBLEMA:, AGITAR:, SOLUCION:, CTA:. "
    "Espanol neutro, sin voseo. Integra la filosofia Endonautas como trasfondo, no como "
    "sermon. Maximo 250 palabras. Es para voz humana real, no TTS."
)


def generate_from_topic(topic: dict) -> str:
    from app.performance_learnings import learnings_prompt_context

    philosophy = random.choice(list(PHILOSOPHIES.keys()))
    phil_text = PHILOSOPHIES[philosophy]
    prompt = (
        f"{SYSTEM}\n\n"
        f"Tematica de inspiracion (un video relacionado que esta andando bien en YouTube, "
        f"no lo copies, usalo solo como referencia del angulo que interesa a la audiencia):\n"
        f"- Keyword: {topic['keyword']}\n"
        f"- Titulo de referencia: {topic['title']}\n\n"
        f"Filosofia Endonautas a integrar: {phil_text}"
        f"{learnings_prompt_context()}\n"
        f"Genera el guion con los 5 encabezados."
    )
    return ask_text(prompt)
