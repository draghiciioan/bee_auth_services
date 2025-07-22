import importlib
import json
import logging
from utils.settings import settings


def test_json_logging_enabled(monkeypatch, capsys):
    monkeypatch.setattr(settings, "environment", "production")
    import main as main_mod
    main_mod = importlib.reload(main_mod)

    async def dummy_init(*args, **kwargs):
        pass

    monkeypatch.setattr(main_mod.FastAPILimiter, "init", dummy_init)
    monkeypatch.setattr(main_mod.redis, "from_url", lambda *a, **k: None)

    capsys.readouterr()  # clear any startup logs

    logging.getLogger().info(
        "json test", extra={"user_id": "42", "endpoint": "/test"}
    )
    captured = capsys.readouterr()
    output = captured.out.strip() or captured.err.strip()
    log = json.loads(output)
    assert log["message"] == "json test"
    assert log["level"] == "INFO"
    assert log["user_id"] == "42"
    assert log["endpoint"] == "/test"

