# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A Project Management MVP: a Kanban board web app with drag-and-drop cards, column renaming, and an AI chat sidebar. Login is hardcoded (`user` / `password`). One board per user. Runs locally in Docker.

## Architecture

**Multi-stage Docker build** (`Dockerfile`):
1. Node 20 builds the Next.js frontend (`frontend/`) into a static export at `frontend/out/`
2. Python 3.12 runtime runs FastAPI, copies the static export into `backend/public/`, and serves it at `/`

The FastAPI backend (`backend/main.py`) serves the built frontend as static files and exposes API routes under `/api/`. There is no separate dev server in production — everything goes through port 8000.

**Frontend** (`frontend/`): Next.js 16 / React 19, Tailwind CSS v4, `@dnd-kit` for drag-and-drop. Board state and types live in `src/lib/kanban.ts`. Main components: `KanbanBoard`, `KanbanColumn`, `KanbanCard`, `KanbanCardPreview`, `NewCardForm`.

**Backend** (`backend/main.py`): FastAPI. Env vars loaded from `.env` at project root. AI calls go through OpenRouter (env var: `OPENROUTER_API_KEY`); use model `openai/gpt-oss-120b:free`. SQLite for persistence (created on startup if absent).

## Running the app

```sh
# Build and start (Mac/Linux) — runs at http://localhost:8000
./scripts/start.sh

# Stop
./scripts/stop.sh
```

The scripts build the Docker image and run the container with `--env-file .env`.

## Frontend development

```sh
cd frontend
npm install
npm run dev          # local Next.js dev server (no backend)
npm run build        # static export used by Docker
npm run test:unit    # vitest unit tests
npm run test:e2e     # playwright end-to-end tests
npm run test:all     # both
```

Run a single unit test file: `npx vitest run src/lib/kanban.test.ts`

## Backend development

```sh
cd backend
uv pip install -e ".[test]"
pytest               # run all backend tests
```

## Color scheme

| Purpose | Hex |
|---|---|
| Accent Yellow | `#ecad0a` |
| Blue Primary | `#209dd7` |
| Purple Secondary | `#753991` |
| Dark Navy | `#032147` |
| Gray Text | `#888888` |

## Coding standards

- No over-engineering. No unnecessary defensive programming. No extra features.
- No emojis, ever.
- Identify root cause before fixing — prove with evidence, then fix.
- Use latest idiomatic library approaches.
- Keep READMEs and docs minimal.
