# profile-service

Microservicio de **perfil del afiliado** de la sucursal virtual de Kenko. Es la fuente de verdad de
los datos personales. Forma parte de un sistema orientado a eventos (Authentication, Profile,
Documents, Appointments, Notifications); los servicios no se llaman entre sí por HTTP.

> Estado: API de consulta y actualización implementada; falta integrar la mensajería asíncrona y Terraform.

## Requisitos

- Windows con WSL2 (Ubuntu). El proyecto debe vivir en el sistema de archivos de WSL (`~/`), no en `/mnt/c`.
- Docker y Docker Compose (en WSL, Docker Desktop con la integración de WSL o el daemon de Docker instalado en Ubuntu).
- Para desarrollo local: Python 3.12 y `uv`. La versión de Python está indicada en `.python-version`.

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

Ejecución local con uv (requiere la BD de Docker publicada en el host):

```bash
uv sync --locked
docker compose up -d profile-db
TEST_DATABASE_URL=postgresql+psycopg://profile:profile@localhost:5432/profile_test uv run --locked pytest
uv run --locked ruff check . && uv run --locked ruff format --check .
```

Las dependencias y sus versiones exactas se declaran en `pyproject.toml`; `uv.lock` fija también
las dependencias transitivas. Usa `uv sync --locked` para instalar sin modificar el lockfile.
Docker instala runtime con `uv sync --locked --no-dev` y el stage de pruebas añade el grupo de
desarrollo desde el mismo lockfile. uv está fijado a la versión 0.9.9 en el Dockerfile.

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

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | No | Proceso y conexión a BD. 200 si todo está bien, 503 si la BD no responde. |
| GET | `/api/v1/profiles/me` | Bearer JWT | Perfil del usuario autenticado. 404 si aún no existe. |
| PUT | `/api/v1/profiles/me` | Bearer JWT | Actualiza campos editables. Publica `ProfileUpdated` solo si cambia algún campo del evento. |

**`PUT /api/v1/profiles/me`:** campos editables y reglas:

| Campo | Tipo | Reglas |
|---|---|---|
| `phone` | string | E.164 (`+573001234567`). No admite `null`. |
| `address` | `{line, city}` | Ambos obligatorios si se envía. No admite `null`. |
| `department` | string o `null` | `null` lo borra. No viaja en eventos. |
| `emergencyContact` | `{name, phone}` o `null` | `null` borra nombre y teléfono. Si se envía, ambos son obligatorios. |

- Los campos omitidos no cambian. Un cuerpo vacío `{}` no escribe nada.
- Campos no editables (`email`, `documentType`, `documentNumber`, `birthDate`, `userId`, ...) devuelven 422.
- Si los valores enviados son iguales a los actuales, no hay escritura ni evento y `updatedAt` no cambia.
- Un cambio que solo toca `department` actualiza la BD pero no publica evento.
- El evento `ProfileUpdated` lleva el estado completo y `changedFields` en el orden `phone`, `address`, `emergencyContact`.
- El `correlationId` del evento es el header `X-Correlation-Id` de la petición.

**Autenticación:** el token se envía en `Authorization: Bearer <jwt>`. El servicio solo valida la firma,
`exp`, `sub` (UUID = userId) e `iss`/`aud` si están configurados. El `userId` se toma **solo** del token;
nunca de la URL ni del cuerpo. Sin token válido: 401 `UNAUTHORIZED`.

**Respuestas JSON:** los campos van en camelCase (igual que los eventos), por ejemplo `firstName`,
`address.line`, `emergencyContact`.

Todas las respuestas incluyen `X-Correlation-Id`. Si el cliente lo envía como UUID válido, se reutiliza;
si no, se genera uno. Los errores usan el formato `{"error": {"code", "message", "correlationId", "details"?}}`.

Generar un token de prueba firmado con la `JWT_SECRET` del `.env` (solo desarrollo; se ejecuta en `profile-api`
para usar la misma clave que la API):

```bash
TOKEN=$(docker compose exec -T profile-api python -c "import uuid,datetime,jwt;from app.config import get_settings as g;s=g();print(jwt.encode({'sub':str(uuid.uuid4()),'exp':datetime.datetime.now(datetime.UTC)+datetime.timedelta(minutes=15)},s.jwt_secret.get_secret_value(),algorithm='HS256'))")
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/profiles/me
```

## Pendiente

- **JWT (TODO):** confirmar con el equipo de Authentication el algoritmo definitivo y los claims. Hoy se
  exige `exp` y `sub` (UUID). `email` y `role` están pendientes de confirmar y no se usan. Además, PyJWT
  rechaza un token con claim `aud` si `JWT_AUDIENCE` no está configurado; confirmar si Authentication lo emite.
- **Clave HS256:** `JWT_SECRET` debe tener al menos 32 caracteres (requisito de RFC 7518 para HMAC-SHA256).
- **Tipos de documento (TODO):** `DocumentType` tiene CC, TI, CE y PA. Confirmar la lista completa.
- **Eventos y mensajería (fase 4):** publicación a EventBridge, consumo SQS, worker idempotente y
  `docs/events.md`. Pendiente la decisión sobre LocalStack (requiere token) frente a moto.
  Hoy la API usa `LogEventPublisher`, que solo registra metadatos (sin datos personales).
- **Confirmar con el equipo de eventos:** que un cambio solo de `department` no publique evento
  (el campo no viaja en los eventos).
- **Consistencia BD-evento:** el evento se publica después del commit. Si la publicación falla, el
  cambio queda guardado sin evento. Se resolverá en la fase 4 con el patrón Transactional Outbox.
- **Worker y red compartida `kenko-net`:** se añadirán en la fase 4 junto con el emulador de AWS.
- **Terraform (fase 5):** `infra/terraform/`.
