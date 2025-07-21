from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
import os
from prometheus_fastapi_instrumentator import Instrumentator

from routers import auth as auth_router
from utils import configure_logging


if os.getenv("ENVIRONMENT") == "production":
    configure_logging()

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


@app.get("/")
def read_root():
    return {"message": "BeeConect Auth Service is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service"}


app.include_router(auth_router.router)
