from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
import os
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import JSONResponse
import sentry_sdk

from routers import auth as auth_router
from utils import configure_logging, alert_if_needed


if os.getenv("ENVIRONMENT") == "production":
    configure_logging()

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(dsn=sentry_dsn)

app = FastAPI(title="BeeConect Auth Service")

# Expose Prometheus metrics if ENABLE_METRICS env var is truthy
enable_metrics = os.getenv("ENABLE_METRICS", "false").lower() in {"1", "true", "yes"}
if enable_metrics:
    Instrumentator().instrument(app).expose(app)

# Enable CORS if origins are provided via environment variable
origins_env = os.getenv("CORS_ORIGINS")
if origins_env:
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize rate limiter with Redis connection."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    db = int(os.getenv("REDIS_DB", 0))
    password = os.getenv("REDIS_PASSWORD")
    if password:
        url = f"redis://:{password}@{host}:{port}/{db}"
    else:
        url = f"redis://{host}:{port}/{db}"
    redis_client = redis.from_url(url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_client)


@app.exception_handler(Exception)
async def handle_exceptions(request: Request, exc: Exception):
    await alert_if_needed(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.get("/")
def read_root():
    return {"message": "BeeConect Auth Service is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service"}


app.include_router(auth_router.router)
