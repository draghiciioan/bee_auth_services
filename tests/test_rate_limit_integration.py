import importlib

from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from utils.settings import settings
from models import User
from utils import hash_password
import events.rabbitmq as rabbitmq
import routers.auth as auth_mod
from fastapi_limiter import FastAPILimiter, default_identifier, http_default_callback, ws_default_callback
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base


def _get_app(monkeypatch, redis_client, session):
    monkeypatch.setattr(settings, "environment", None)
    import main as main_mod
    main_mod = importlib.reload(main_mod)
    monkeypatch.setattr(main_mod.redis, "from_url", lambda *a, **k: redis_client)

    async def fake_init(
        redis,
        prefix: str = "fastapi-limiter",
        identifier: callable = default_identifier,
        http_callback: callable = http_default_callback,
        ws_callback: callable = ws_default_callback,
    ) -> None:
        FastAPILimiter.redis = redis
        FastAPILimiter.prefix = prefix
        FastAPILimiter.identifier = identifier
        FastAPILimiter.http_callback = http_callback
        FastAPILimiter.ws_callback = ws_callback
        FastAPILimiter.lua_sha = "fake"

    async def fake_check(self, key):
        redis = FastAPILimiter.redis
        current = int(await redis.get(key) or 0)
        if current > 0:
            if current + 1 > self.times:
                return await redis.pttl(key)
            await redis.incr(key)
            return 0
        await redis.set(key, 1, px=self.milliseconds)
        return 0

    monkeypatch.setattr(FastAPILimiter, "init", fake_init)
    monkeypatch.setattr(RateLimiter, "_check", fake_check)

    async def dummy_emit(*args, **kwargs):
        pass

    monkeypatch.setattr(rabbitmq, "emit_event", dummy_emit)
    monkeypatch.setattr(auth_mod, "emit_event", dummy_emit)

    def override_db():
        yield session

    main_mod.app.dependency_overrides[auth_mod.get_db] = override_db
    return main_mod.app


def create_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    db = SessionLocal()
    return db, engine, connection, transaction


def create_user(session):
    user = User(
        email="rate@example.com",
        hashed_password=hash_password("Secret123!"),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_login_rate_limit_exceeded(monkeypatch):
    redis_client = FakeRedis(decode_responses=True)
    session, engine, connection, transaction = create_session()
    app = _get_app(monkeypatch, redis_client, session)
    user = create_user(session)

    with TestClient(app) as client:
        payload = {"email": user.email, "password": "Secret123!"}
        for _ in range(5):
            resp = client.post("/v1/auth/login", json=payload)
            assert resp.status_code == 200
        resp = client.post("/v1/auth/login", json=payload)
        assert resp.status_code == 429
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()
