import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routers import videos, hooks, scripts, calendar, stats, reel_pipeline, telegram_webhook, youtube_credential

load_dotenv()

init_db()

app = FastAPI(title="yt-automation", version="0.1.0")

# CORS: acepta los frontends conocidos (InfinityFree y Coolify sslip.io).
# Se lee CORS_ORIGIN si existe, pero siempre se suma el origen de Coolify por defecto.
cors_env = os.getenv("CORS_ORIGIN", "")
origins = [o.strip() for o in cors_env.split(",") if o.strip()]
defaults = [
    "https://yt-automation.freedev.app",
    "https://yt-automation.146.181.39.4.sslip.io",
    "https://yt-frontend.146.181.39.4.sslip.io",
]
for d in defaults:
    if d not in origins:
        origins.append(d)
if not origins:
    origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(hooks.router)
app.include_router(scripts.router)
app.include_router(calendar.router)
app.include_router(stats.router)
app.include_router(reel_pipeline.router)
app.include_router(telegram_webhook.router)
app.include_router(youtube_credential.router)


@app.get("/")
def root():
    return {"service": "yt-automation", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}
