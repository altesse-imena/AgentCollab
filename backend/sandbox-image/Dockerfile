# Image that runs generated tests. Kept minimal: Python + pytest, no network at run time.
# Bake extra dependencies in here if your target repos need them.
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest==8.3.5
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /work
