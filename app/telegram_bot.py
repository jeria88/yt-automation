"""Bot de Telegram bidireccional, dedicado a yt-automation (NO reusa el bot de Hermes)."""
import os

import httpx

BASE = "https://api.telegram.org/bot{token}"


def _token() -> str:
    return os.environ["TELEGRAM_BOT_TOKEN_RPC"]


def _url(method: str) -> str:
    return f"{BASE.format(token=_token())}/{method}"


def send_message(chat_id: str, text: str, buttons: list[list[tuple[str, str]]] | None = None) -> dict:
    """buttons: lista de filas, cada fila lista de (texto, callback_data)."""
    payload = {"chat_id": chat_id, "text": text}
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": t, "callback_data": cb} for t, cb in row] for row in buttons
            ]
        }
    resp = httpx.post(_url("sendMessage"), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["result"]


def answer_callback_query(callback_query_id: str, text: str = "") -> None:
    httpx.post(_url("answerCallbackQuery"), json={
        "callback_query_id": callback_query_id, "text": text,
    }, timeout=15)


def download_voice(file_id: str, dest_path: str) -> None:
    resp = httpx.get(_url("getFile"), params={"file_id": file_id}, timeout=30)
    resp.raise_for_status()
    file_path = resp.json()["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{_token()}/{file_path}"
    with httpx.stream("GET", file_url, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)


def set_webhook(url: str) -> dict:
    resp = httpx.post(_url("setWebhook"), json={"url": url}, timeout=30)
    resp.raise_for_status()
    return resp.json()
