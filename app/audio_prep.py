"""Preprocesa el audio real de Franco antes de transcribir: corta silencios
largos (lee muy pausado) y acelera el ritmo (lee "muy academico"). Todo con
ffmpeg, sin servicios pagos."""
import subprocess

SILENCE_FILTER = "silenceremove=stop_periods=-1:stop_duration=0.6:stop_threshold=-35dB"
# feedback Franco: 1.3 quedo dificil de entender ("demasiado acelerado").
# 1.12 es un empujon mas sutil - corrige el ritmo academico sin sacrificar
# inteligibilidad.
SPEED_FACTOR = 1.12


def prepare_audio(src_path: str, dst_path: str, speed: float = SPEED_FACTOR) -> str:
    subprocess.run(
        ["ffmpeg", "-y", "-i", src_path, "-af", f"{SILENCE_FILTER},atempo={speed}", dst_path],
        check=True, capture_output=True, timeout=120,
    )
    return dst_path
