# syntax=docker/dockerfile:1

# uv está versionado explícitamente para builds reproducibles.
FROM ghcr.io/astral-sh/uv:0.9.9 AS uv

FROM python:3.12-slim AS base
COPY --from=uv /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Lock reproducible dependencies de runtime. --no-install-project es explícito:
# esta app no se instala como paquete Python (tool.uv.package = false).
FROM base AS runtime-deps
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM base AS runtime
RUN groupadd --system app && useradd --system --gid app --uid 10001 --no-create-home app
COPY --from=runtime-deps --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Stage de pruebas: añade el grupo dev al mismo lockfile y conserva el usuario no root.
FROM runtime AS test
USER root
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --group dev --no-install-project
COPY --chown=app:app tests ./tests
USER app
CMD ["pytest", "-p", "no:cacheprovider"]
