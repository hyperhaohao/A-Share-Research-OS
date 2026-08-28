# Backend: Python 3.11 + uv + FastAPI (matches local dev exactly)
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scheduler_worker.py ./scheduler_worker.py

RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --no-install-project

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Healthcheck hits the live /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

# Migrations are applied by the entrypoint before serving
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
