# profile-service

Microservicio de **perfil del afiliado** de la sucursal virtual de Kenko. Es la fuente de verdad de
los datos personales. Forma parte de un sistema orientado a eventos (Authentication, Profile,
Documents, Appointments, Notifications); los servicios no se llaman entre sí por HTTP.

> Estado: **bloque 2 de la implementación**. Hay configuración, logging, errores, base de datos,
> migraciones y `/health`. Todavía no hay endpoints de perfil, JWT ni eventos (ver [Pendiente](#pendiente)).

## Requisitos

- Windows con WSL2 (Ubuntu). El proyecto debe vivir en el sistema de archivos de WSL (`~/`), no en `/mnt/c`.
- Docker y Docker Compose (en WSL, Docker Desktop con la integración de WSL o el daemon de Docker instalado en Ubuntu).
- Para ejecutar pruebas o ruff fuera de Docker: Python 3.12 y `uv`. Esto es opcional; todo puede hacerse en contenedores.

## Puesta en marcha

```bash
cp .env.example .env              # ajusta valores si hace falta; .env nunca se versiona
docker compose up --build         # levanta profile-db, aplica migraciones y arranca la API
curl -i localhost:8000/health     # 200 {"status":"ok","database":"ok"}
```

Servicios de `docker-compose.yml`:

| Servicio          | Función                                                         |
|-------------------|-----------------------------------------------------------------|
| `profile-db`      | PostgreSQL 16 con volumen nombrado `profile-db-data`.           |
| `profile-migrate` | Ejecuta `alembic upgrade head` y termina (uso único).           |
| `profile-api`     | API FastAPI (uvicorn) en el puerto 8000.                        |
| `profile-tests`   | Imagen de pruebas (perfil `test`). No se levanta por defecto.   |

## Migraciones (Alembic)

```bash
docker compose run --rm profile-migrate alembic current            # revisión actual
docker compose run --rm profile-migrate alembic upgrade head       # aplicar pendientes
docker compose run --rm profile-migrate alembic downgrade -1       # revertir una
```

Para crear una migración a partir de los modelos (la BD debe estar levantada):

```bash
docker compose run --rm profile-migrate alembic revision --autogenerate -m "descripcion"
```

Revisa siempre el archivo generado en `migrations/versions/` antes de confirmarlo.

## Pruebas

```bash
docker compose --profile test run --rm profile-tests       # unit + integración contra Postgres real
```

Las pruebas de integración usan la base `profile_test` (se crea automáticamente). Nunca apuntan a
la base de desarrollo: la configuración exige que el nombre termine en `_test`.

Ejecución local (opcional), con la BD de Docker publicada en el host:

```bash
uv venv .venv --python 3.12 && uv pip install -p .venv -r requirements-dev.txt
docker compose up -d profile-db
TEST_DATABASE_URL=postgresql+psycopg://profile:profile@localhost:5432/profile_test .venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Estructura

```
app/
  main.py                 fábrica create_app(), lifespan, middleware de correlación
  config.py               Settings (pydantic-settings) desde variables de entorno
  api/                    rutas, schemas y dependencias (sesión de BD)
  services/               lógica de negocio (fase 3)
  repositories/           acceso a datos
  domain/                 excepciones y enumeraciones de negocio
  db/                     Base, sesión/engine y modelos SQLAlchemy
  events/                 contrato de eventos, publicador/consumidor (fase 4)
  workers/                consumidor SQS (fase 4)
  core/                   logging JSON, errores uniformes, ids UUID v7, tiempo
migrations/               Alembic (env.py + versiones)
tests/                    unit/ (sin BD) e integration/ (Postgres real)
```

La arquitectura es por capas: `api -> services -> repositories`. Los services no importan
infraestructura de AWS; la publicación de eventos se inyectará mediante interfaces.

## Configuración

Todas las variables están documentadas en `.env.example`. Resumen:

| Variable | Descripción |
|---|---|
| `ENVIRONMENT` | `dev` o `prod`. En `prod` se desactivan `/docs` y `/openapi.json`. |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` o `ERROR`. |
| `DATABASE_URL` | URL de SQLAlchemy con driver psycopg v3. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales que usa el contenedor `profile-db`. |
| `JWT_ALGORITHM` | `HS256` (dev, con `JWT_SECRET`) o `RS256` (con `JWT_PUBLIC_KEY`). |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Opcionales. Si están definidos, se validan los claims `iss` y `aud`. |

## Endpoints actuales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Proceso y conexión a BD. 200 si todo está bien, 503 si la BD no responde. |

Todas las respuestas incluyen `X-Correlation-Id`. Si el cliente lo envía como UUID válido, se reutiliza;
si no, se genera uno. Los errores usan el formato `{"error": {"code", "message", "correlationId", "details"?}}`.

## Pendiente

- **JWT (TODO):** confirmar con el equipo de Authentication el algoritmo definitivo y los claims. Hoy se
  asume `sub` = userId (UUID); `email` y `role` están pendientes de confirmar. No se validan todavía.
- **Tipos de documento (TODO):** `DocumentType` tiene CC, TI, CE y PA. Confirmar la lista completa.
- **Eventos y mensajería (fase 4):** publicación a EventBridge, consumo SQS, worker idempotente y
  `docs/events.md`. Pendiente la decisión sobre LocalStack (requiere token) frente a moto.
- **Worker y red compartida `kenko-net`:** se añadirán en la fase 4 junto con el emulador de AWS.
- **Terraform (fase 5):** `infra/terraform/`.
