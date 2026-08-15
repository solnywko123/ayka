FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# api/app читает site/content/pricing.json как единый источник правды (PRICING_PATH) —
# поэтому в образ попадает и site/content целиком, а рабочая директория контейнера
# соответствует репозиторию, а не только каталогу api/.
COPY api/ ./api/
COPY site/content/ ./site/content/

WORKDIR /app/api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# В проде — alembic upgrade перед стартом, затем gunicorn с uvicorn workers.
CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000"]
