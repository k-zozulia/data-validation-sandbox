from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.services import storage
from app.models.schemas import HealthResponse, AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_redis()
    yield
    await storage.close_redis()


app = FastAPI(title="Data Validation Sandbox API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": exc.error, "detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500,
                        content={"error": "internal_error",
                                 "detail": "Unexpected server error"})


@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        ok = await storage.ping()
        return HealthResponse(status="ok", redis="up" if ok else "down")
    except Exception:
        return JSONResponse(status_code=503,
                            content={"status": "degraded", "redis": "down"})


from app.routers import profile, validate, jobs

app.include_router(profile.router)
app.include_router(validate.router)
app.include_router(jobs.router)