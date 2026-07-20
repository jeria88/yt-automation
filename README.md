# yt-automation

Sistema de automatización de contenido para canales de YouTube faceless (desarrollo
personal / motivación). Combina un tablero kanban de pipeline de videos, una biblioteca
de ganchos virales, un generador de guiones estilo Hormozi con filosofía Endonautas,
un calendario de publicación y stats.

## Arquitectura

- **Frontend** (HTML/JS estático): https://yt-automation.freedev.app — hosteado en
  InfinityFree vía FTP. No corre backend (plan gratis de InfinityFree solo sirve
  PHP/MySQL/estático), así que consume la API por HTTPS.
- **Backend** (FastAPI + SQLite): https://yt-automation.146.181.39.4.sslip.io —
  deployado en Oracle (ARM, 12 GB) vía Coolify (Docker). Expuesto por Traefik con
  certificado Let's Encrypt sobre el dominio `*.146.181.39.4.sslip.io`.
- **CORS**: el backend solo acepta el origen `https://yt-automation.freedev.app`.

> Nota: `yt-automation.freedev.app` es un subdominio de InfinityFree (freedev.app está
> en su Public Suffix List). No se controla su DNS, por eso el frontend queda fijo ahí
> y el backend vive en Oracle.

## Módulos

| Módulo | Ruta API | Descripción |
|---|---|---|
| Pipeline kanban | `/api/videos` | Etapas: idea → guion → audio → edicion → miniatura → publicado |
| Biblioteca de ganchos | `/api/hooks` | Ganchos manuales + scrapeo Reddit (fallback mock si no hay creds) |
| Generador de guiones | `/api/scripts` | Estructura Hormozi (HOOK/PROBLEMA/AGITAR/SOLUCION/CTA) + filosofía Endonautas |
| Calendario | `/api/posts` | Programación de publicaciones por video |
| Stats | `/api/stats` | Totales, conteo por etapa, próximas publicaciones |

## Stack

- Backend: Python 3.11, FastAPI, Uvicorn, SQLAlchemy, SQLite.
- LLM: OpenRouter (modelo free `tencent/hy3:free`) para expandir guiones. Sin key,
  devuelve un esqueleto rellenable.
- Deploy: Docker + Coolify (self-host en Oracle).
- Frontend: HTML5 + CSS + vanilla JS (sin build step).

## Estructura

```
yt-automation/
├── backend/                 # API FastAPI (deployada en Oracle/Coolify)
│   ├── app/
│   │   ├── main.py          # app, CORS, init_db
│   │   ├── auth.py          # token bearer
│   │   ├── db.py            # SQLAlchemy models + init
│   │   ├── routers/         # videos, hooks, scripts, calendar, stats
│   │   ├── scrapers/        # reddit.py (scrapeo con fallback mock)
│   │   └── prompts/         # hormozi.py (plantillas + filosofía Endonautas)
│   ├── tests/               # tests TDD (pytest)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
├── htdocs/                  # Frontend estático (subido a InfinityFree por FTP)
│   ├── index.html
│   ├── css/style.css
│   └── js/ (api.js, app.js, views/*)
├── deploy_ftp.py            # sube htdocs/ a InfinityFree
├── verify_gsc.py            # sube archivo de verificación de Search Console
└── PLAN.md                  # plan de implementación
```

## Desarrollo local (backend)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # editá API_TOKEN / OPENROUTER_KEY
pytest tests/ -v            # 13 tests
uvicorn app.main:app --reload --port 8000
```

## Deploy backend (Coolify / Oracle)

1. El repo debe estar en GitHub en la rama `main` (sin secretos en el historial).
2. En Coolify: New Application → Git → `jeria88/yt-automation`, Branch `main`,
   Build Pack `Dockerfile`, Base Directory `/`, Port `8000`.
3. Environment variables:
   - `API_TOKEN` — token del admin (usado por el frontend en el login)
   - `OPENROUTER_KEY` — key de OpenRouter (solo si querés LLM; si no, esqueleto)
   - `OPENROUTER_MODEL=tencent/hy3:free`
   - `CORS_ORIGIN=https://yt-automation.freedev.app`
4. Domain: `yt-automation.146.181.39.4.sslip.io` (sslips resuelve a la IP de Oracle).
5. Deploy. Verificar: `curl https://yt-automation.146.181.39.4.sslip.io/health` → 200.

## Deploy frontend (InfinityFree)

```bash
cd yt-automation
FTP_PASS='<tu-pass-ftp>' python3 deploy_ftp.py
```

Sube `htdocs/` a `ftpupload.net:/htdocs`. El `index.html` ya trae la API Base URL
apuntando al backend de Oracle.

## Google Search Console

1. Search Console → Añadir propiedad → Prefijo de URL →
   `https://yt-automation.freedev.app/`.
2. Método "Archivo HTML": descargá `google<codigo>.html`.
3. `python3 verify_gsc.py google<codigo>.html` (sube el archivo a htdocs).
4. Clic "Verificar".
   (No usar Domain property: freedev.app es de InfinityFree, sin control DNS.)

## Modelo de datos

- **Video**: id, title, stage, hook_id, notes, due, created_at
- **Hook**: id, text, source (manual/reddit/youtube/trends), tags, created_at
- **Script**: id, video_id, body, philosophy (espejo/sombra/pilares), created_at
- **Post**: id, video_id, scheduled_at, status (planned/published/failed), platform

## Seguridad

- El token de API se envía como `Authorization: Bearer` desde el frontend.
- La key de OpenRouter vive SOLO en las env vars de Coolify, nunca en el repo.
- El frontend no genera TTS: prepara el guion para que Franco grabe la voz humana.

## Pendientes / mejoras

- Persistencia: SQLite está dentro del container de Coolify; para producción usar
  MySQL de InfinityFree o un volumen persistente en Oracle.
- Scrapeo Reddit real: requiere `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` en env.
- Webhook de deploy: conectar push a `main` con redeploy automático en Coolify.
