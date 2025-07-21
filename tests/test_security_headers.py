import importlib
from fastapi.testclient import TestClient


def _get_app(monkeypatch, prod: bool):
    if prod:
        monkeypatch.setenv("ENVIRONMENT", "production")
    else:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    import main as main_mod
    main_mod = importlib.reload(main_mod)

    async def dummy_init(*args, **kwargs):
        pass

    monkeypatch.setattr(main_mod.FastAPILimiter, "init", dummy_init)
    monkeypatch.setattr(main_mod.redis, "from_url", lambda *a, **k: None)
    return main_mod.app


def test_security_headers_enabled(monkeypatch):
    app = _get_app(monkeypatch, True)
    with TestClient(app) as client:
        response = client.get("/")
        headers = response.headers
        assert headers["x-frame-options"] == "DENY"
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
        assert "default-src" in headers["content-security-policy"]


def test_security_headers_disabled(monkeypatch):
    app = _get_app(monkeypatch, False)
    with TestClient(app) as client:
        response = client.get("/")
        assert "x-frame-options" not in response.headers


