import importlib
from fastapi.testclient import TestClient


def _get_app(monkeypatch, enabled: bool) -> object:
    if enabled:
        monkeypatch.setenv("ENABLE_METRICS", "1")
    else:
        monkeypatch.delenv("ENABLE_METRICS", raising=False)
    import main as main_mod
    main_mod = importlib.reload(main_mod)

    async def dummy_init(*args, **kwargs):
        pass

    monkeypatch.setattr(main_mod.FastAPILimiter, "init", dummy_init)
    monkeypatch.setattr(main_mod.redis, "from_url", lambda *a, **k: None)
    return main_mod.app


def test_metrics_enabled(monkeypatch):
    app = _get_app(monkeypatch, True)
    with TestClient(app) as client:
        response = client.get("/metrics")
        assert response.status_code == 200


def test_metrics_disabled(monkeypatch):
    app = _get_app(monkeypatch, False)
    with TestClient(app) as client:
        response = client.get("/metrics")
        assert response.status_code == 404
