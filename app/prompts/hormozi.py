# Plantillas del generador estilo Hormozi + filosofía Endonautas.
# Filosofía (memoria Franco): Ley Espejo / Sombra / Pilares.

PHILOSOPHIES = {
    "espejo": (
        "El mundo es un espejo: lo que ves afuera es el reflejo de lo que habitas adentro. "
        "Cambia la mirada y cambia la realidad."
    ),
    "sombra": (
        "Tu sombra es la parte de ti que relegaste. Integrarla no es eliminarla, es hacerte "
        "dueño de tu fuerza negada."
    ),
    "pilares": (
        "Todo se sostiene sobre pocos pilares. Identifícalos y sostén lo esencial; lo demás "
        "colapsa sin que importe."
    ),
}

PROMPT_SYSTEM = (
    "Eres un guionista de YouTube faceless para un canal de desarrollo personal / motivación. "
    "Escribe en español neutro (sin voseo). Usa la estructura de Alex Hormozi: "
    "hook -> problema -> agitar -> solucion -> CTA. Integra la filosofía Endonautas indicada "
    "como trasfondo, no como sermón. Máximo 250 palabras. Sin TTS: es para voz humana."
)


def build_skeleton(hook: str, philosophy: str) -> str:
    phil = PHILOSOPHIES.get(philosophy, PHILOSOPHIES["espejo"])
    return (
        f"HOOK:\n{hook}\n\n"
        f"PROBLEMA:\n(Describe el problema real que vive tu audiencia respecto a esto.)\n\n"
        f"AGITAR:\n(Sube la tensión: muestra el costo de no cambiar.)\n\n"
        f"SOLUCION:\n{phil}\n(Explica el cambio concreto paso a paso.)\n\n"
        f"CTA:\n(Suscríbete y comenta: ¿qué reflejo estás listo para cambiar?)\n"
    )


def build_llm_prompt(hook: str, philosophy: str) -> str:
    phil = PHILOSOPHIES.get(philosophy, PHILOSOPHIES["espejo"])
    return (
        f"Gancho inicial: {hook}\n"
        f"Filosofía Endonautas a integrar: {phil}\n"
        "Genera el guion de 5 secciones."
    )
