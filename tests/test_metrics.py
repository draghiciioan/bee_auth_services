import importlib
from fastapi.testclient import TestClient
from utils.settings import settings


def _get_app(monkeypatch, enabled: bool) -> object:
    if enabled:
        monkeypatch.setattr(settings, "enable_metrics", True)
    else:
        monkeypatch.setattr(settings, "enable_metrics", False)
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
        text = response.text
        assert "bee_auth_password_reset_requested_total" in text
        assert "bee_auth_twofa_tokens_generated_total" in text


def test_metrics_disabled(monkeypatch):
    app = _get_app(monkeypatch, False)
    with TestClient(app) as client:
        response = client.get("/metrics")
        assert response.status_code == 404
