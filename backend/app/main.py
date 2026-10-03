import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.config import settings
from app.db import engine
from app.errors import AppException
from app.models.schemas import HealthResponse
from app.routers import datasets, jobs, rule_sets, rules
from app.services.storage import get_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dvs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_storage()                       # fail fast on a misconfigured storage backend
    yield


app = FastAPI(
    title="Data Validation Sandbox API",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": exc.error, "detail": exc.detail, **exc.extra})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(x) for x in first.get("loc", []))
    return JSONResponse(status_code=422,
                        content={"error": "invalid_request",
                                 "detail": f"{where}: {first.get('msg', 'invalid input')}",
                                 "errors": exc.errors()},
                        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500,
                        content={"error": "internal_error", "detail": "Unexpected server error"})


api = APIRouter(prefix="/api")


@api.get("/health", response_model=HealthResponse)
def health():
    def check(fn) -> str:
        try:
            return "up" if fn() is not False else "down"
        except Exception:
            return "down"

    def db_ok():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def redis_ok():
        if settings.inline_jobs:
            return True
        import redis
        return redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()

    body = HealthResponse(
        status="ok",
        database=check(db_ok),
        redis="n/a" if settings.inline_jobs else check(redis_ok),
        storage=check(lambda: get_storage().ping()),
        inline_jobs=settings.inline_jobs,
    )
    if "down" in (body.database, body.redis, body.storage):
        body.status = "degraded"
        return JSONResponse(status_code=503, content=body.model_dump())
    return body


api.include_router(datasets.router)
api.include_router(jobs.router)
api.include_router(rules.router)
api.include_router(rule_sets.router)
app.include_router(api)
