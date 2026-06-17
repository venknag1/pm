FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

COPY backend/pyproject.toml ./backend/pyproject.toml
RUN uv pip install --system fastapi uvicorn[standard] python-dotenv bcrypt itsdangerous openai

COPY backend/ ./backend
COPY --from=frontend-builder /app/frontend/out ./backend/public

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
