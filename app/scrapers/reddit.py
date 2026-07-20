import os


def fetch_reddit(query: str, limit: int = 10) -> list[dict]:
    """Devuelve ganchos virales desde Reddit. Si no hay creds configuradas,
    devuelve datos mock deterministas para que el sistema funcione sin API."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "yt-automation/0.1")

    if not client_id or not client_secret:
        return _mock(query, limit)

    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        results = []
        for post in reddit.subreddit("all").search(query, limit=limit, sort="top"):
            results.append({
                "text": post.title,
                "source": "reddit",
                "tags": query,
                "score": post.score,
            })
        return results
    except Exception:
        return _mock(query, limit)


def _mock(query: str, limit: int) -> list[dict]:
    base = [
        f"¿Por qué el {query} nunca funciona (y lo que nadie te dice)",
        f"La verdad incómoda sobre el {query} que cambió mi vida",
        f"Deja de perder tiempo con el {query}: haz esto instead",
        f"El error #1 en el {query} que arruina tus resultados",
        f"3 lecciones de {query} que ojalá supiera a los 20",
    ]
    return [{"text": t, "source": "reddit", "tags": query, "score": 0} for t in base[:limit]]
