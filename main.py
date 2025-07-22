from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import JSONResponse
import sentry_sdk

from routers import auth as auth_router
from utils import configure_logging, alert_if_needed, SecurityHeadersMiddleware
from utils.rate_limit import user_rate_limit_key
from utils.settings import settings

is_production = settings.environment == "production"

if is_production:
    configure_logging()
sentry_dsn = settings.sentry_dsn
if sentry_dsn:
    sentry_sdk.init(dsn=sentry_dsn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize rate limiter with Redis connection."""
    redis_client = redis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    # Use custom key builder that includes user identifier for rate limiting
    await FastAPILimiter.init(redis_client, identifier=user_rate_limit_key)
    yield


app = FastAPI(title="BeeConect Auth Service", lifespan=lifespan)

# Expose Prometheus metrics if ENABLE_METRICS env var is truthy
enable_metrics = settings.enable_metrics
if enable_metrics:
    Instrumentator().instrument(app).expose(app)

# Enable CORS if origins are provided via environment variable
origins_env = settings.cors_origins
if origins_env:
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if is_production:
    app.add_middleware(SecurityHeadersMiddleware)



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
