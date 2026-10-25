# Recruitment Assistant MVP — CrewAI runtime (AAMAD_TARGET_RUNTIME=crewai)
# One image: FastAPI + built chat page. No GPU.

FROM node:18-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AAMAD_TARGET_RUNTIME=crewai \
    CREWAI_TELEMETRY_OPT_OUT=true \
    PORT=8000

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/backend /app/src/backend
COPY deploy /app/deploy
COPY --from=frontend /src/frontend/dist /app/src/frontend/dist

RUN chmod +x /app/deploy/entrypoint.sh \
    && mkdir -p /app/var/runs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
