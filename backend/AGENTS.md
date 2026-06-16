# Backend Agent Notes

## Purpose

This file documents the current `backend/` scaffold and how it is set up for the Project Management MVP.

## Current backend structure

- `backend/main.py`: FastAPI application entry point.
- `backend/pyproject.toml`: dependency manifest for the Python backend.
- `backend/public/index.html`: example static HTML served at `/`.
- `backend/AGENTS.md`: this file.

## App behavior

- The backend serves a simple static page from `/` using `StaticFiles`.
- A health route is available at `/api/health`.
- The app is designed as a minimal scaffold for future backend API expansion.

## Docker support

- The root `Dockerfile` uses Python 3.12 slim.
- It installs `uv` and uses `uv install` to install backend dependencies from `backend/pyproject.toml`.
- The container runs `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.

## Next steps

The backend is ready to be extended with authentication, database persistence, and API routes for the Kanban board.
