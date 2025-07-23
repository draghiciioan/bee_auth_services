import importlib
from utils.settings import settings


def _get_app(monkeypatch):
    monkeypatch.setattr(settings, "environment", None)
    import main as main_mod
    main_mod = importlib.reload(main_mod)

    async def dummy_init(*args, **kwargs):
        pass

    monkeypatch.setattr(main_mod.FastAPILimiter, "init", dummy_init)
    monkeypatch.setattr(main_mod.redis, "from_url", lambda *a, **k: None)
    return main_mod.app


def test_auth_openapi_metadata(monkeypatch):
    app = _get_app(monkeypatch)
    schema = app.openapi()
    expected = {
        "/v1/auth/register": ("post", "Register new user", "Create a new user"),
        "/v1/auth/login": ("post", "User login", "Authenticate user"),
        "/v1/auth/social/login": ("get", "Start OAuth login", "Generate"),
        "/v1/auth/social/callback": (
            "post",
            "OAuth callback",
            "Handle provider callback",
        ),
        "/v1/auth/verify-email": (
            "get",
            "Verify email token",
            "Validate email verification",
        ),
        "/v1/auth/verify-2fa": (
            "post",
            "Verify 2FA token",
            "Validate two-factor",
        ),
        "/v1/auth/validate": (
            "get",
            "Validate JWT token",
            "Check if a JWT",
        ),
        "/v1/auth/me": ("get", "Current user info", "Return details"),
    }
    for path, (method, summary, desc_start) in expected.items():
        operation = schema["paths"][path][method]
        assert operation["summary"] == summary
        assert desc_start in operation["description"]
