from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.db.session import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health(request: Request) -> JSONResponse:
    engine = getattr(request.app.state, "engine", None)
    database_ok = engine is not None and check_database(engine)
    status = "ok" if database_ok else "unavailable"
    return JSONResponse(
        status_code=200 if database_ok else 503,
        content={"status": status, "database": "ok" if database_ok else "unavailable"},
    )
