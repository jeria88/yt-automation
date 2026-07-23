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
    "sermon. Maximo 250 palabras. Es para voz humana real, no TTS.\n\n"
    "HOOK: nunca una pregunta abstracta ('¿Alguna vez te has preguntado...?') ni un "
    "saludo/presentacion. Usa la formula 'creencia popular aceptada + por que te esta "
    "danando + promesa de la revelacion' - tiene que sonar contraintuitivo, que el "
    "espectador piense 'un momento, ¿que?'. Mal: '¿Alguna vez te has preguntado sobre tu "
    "sombra interior?'. Bien: 'No tenes un despertar espiritual, estas huyendo de tu "
    "sombra.'\n\n"
    "UN SOLO CONCEPTO por guion: elegi UNA sola realizacion o tecnica de la filosofia "
    "Endonautas y desarrollala completa. Nunca mezcles 2-3 ideas distintas en el mismo "
    "guion aunque esten relacionadas - el video sirve para una sola idea, no un resumen.\n\n"
    "PROBLEMA/AGITAR: traduce el concepto psicologico a una situacion de vida real "
    "reconocible, nunca dejes la jerga sin traducir. Mal: 'la proyeccion del "
    "inconsciente'. Bien: 'por que siempre terminas con el mismo tipo de pareja toxica'."
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
