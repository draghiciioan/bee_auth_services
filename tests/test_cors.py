import importlib
from fastapi.testclient import TestClient


def test_cors_headers(monkeypatch):
    """Ensure CORS headers are returned when origins are configured."""
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com")

    import main as main_mod
    main_mod = importlib.reload(main_mod)

    async def dummy_init(*args, **kwargs):
        pass

    monkeypatch.setattr(main_mod.FastAPILimiter, "init", dummy_init)
    monkeypatch.setattr(main_mod.redis, "from_url", lambda *a, **k: None)

    with TestClient(main_mod.app) as client:
        response = client.get("/", headers={"Origin": "https://example.com"})
        assert response.headers.get("access-control-allow-origin") == "https://example.com"
