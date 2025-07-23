import asyncio
import importlib

import pytest

from utils.settings import settings
from utils.metrics import error_counter


def _load_alerts(monkeypatch, threshold: int):
    monkeypatch.setattr(settings, "alertmanager_url", "http://alertmanager")
    monkeypatch.setattr(settings, "error_alert_threshold", threshold)
    import utils.alerts as alerts_mod
    return importlib.reload(alerts_mod)


def test_alert_triggered_at_threshold(monkeypatch):
    alerts = _load_alerts(monkeypatch, threshold=3)
    calls = []

    def fake_urlopen(*args, **kwargs):
        calls.append(1)

    monkeypatch.setattr(alerts.urlrequest, "urlopen", fake_urlopen)
    error_counter._value.set(0)

    for _ in range(alerts.ERROR_ALERT_THRESHOLD):
        asyncio.run(alerts.alert_if_needed(Exception("boom")))

    assert len(calls) == 1


def test_no_alert_before_threshold(monkeypatch):
    alerts = _load_alerts(monkeypatch, threshold=3)
    calls = []

    def fake_urlopen(*args, **kwargs):
        calls.append(1)

    monkeypatch.setattr(alerts.urlrequest, "urlopen", fake_urlopen)
    error_counter._value.set(0)

    for _ in range(alerts.ERROR_ALERT_THRESHOLD - 1):
        asyncio.run(alerts.alert_if_needed(Exception("boom")))

    assert len(calls) == 0
