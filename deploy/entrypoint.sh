#!/bin/sh
# Single-process container start. Bind all container interfaces so the
# published host port can reach Uvicorn. Compose publishes that port on
# 127.0.0.1 only. HOST from .env is intentionally ignored here.
set -eu
cd /app
exec python -m uvicorn deploy.static_app:app --app-dir /app --host 0.0.0.0 --port "${PORT:-8000}"
