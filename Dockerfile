# One image serving the API and the built UI. Intended for a replay-only demo
# (AGENTCOLLAB_LIVE_RUNS=false): live runs need a Docker daemon for the sandbox.

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY backend/pyproject.toml backend/
COPY backend/agentcollab backend/agentcollab
COPY backend/sandbox-image backend/sandbox-image
RUN pip install -e ./backend
COPY evals evals
COPY demo demo
COPY --from=web /web/dist static
RUN useradd --create-home app && mkdir data && chown app data
USER app
ENV AGENTCOLLAB_STATIC_DIR=/app/static \
    AGENTCOLLAB_SEED_FILE=/app/demo/runs.json \
    DATABASE_URL=sqlite:////app/data/agentcollab.db \
    AGENTCOLLAB_LIVE_RUNS=false \
    AGENTCOLLAB_TRUST_PROXY=true
EXPOSE 8000
CMD ["sh", "-c", "uvicorn agentcollab.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
