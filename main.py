from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
import os

from routers import auth as auth_router


app = FastAPI(title="BeeConect Auth Service")


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
