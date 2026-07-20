import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routers import videos, hooks, scripts, calendar, stats

load_dotenv()

init_db()

app = FastAPI(title="yt-automation", version="0.1.0")

cors_origin = os.getenv("CORS_ORIGIN", "https://yt-automation.freedev.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(hooks.router)
app.include_router(scripts.router)
app.include_router(calendar.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {"service": "yt-automation", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}
