# syntax=docker/dockerfile:1

# Imagen única para API, worker (fase 4), migraciones y tests.
# El comando cambia según el servicio de docker-compose.yml.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

FROM base AS builder
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS runtime
RUN groupadd --system app && useradd --system --gid app --uid 10001 --no-create-home app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
USER root
COPY requirements.txt requirements-dev.txt pyproject.toml ./
RUN pip install -r requirements-dev.txt
COPY tests ./tests
USER app
CMD ["pytest", "-p", "no:cacheprovider"]
