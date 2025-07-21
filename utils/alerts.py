import asyncio
import json
import os
from urllib import request as urlrequest
from urllib.parse import urljoin

from .metrics import error_counter

ALERTMANAGER_URL = os.getenv("ALERTMANAGER_URL")
ERROR_ALERT_THRESHOLD = int(os.getenv("ERROR_ALERT_THRESHOLD", "10"))


def _post_alert(payload: str) -> None:
    if not ALERTMANAGER_URL:
        return
    req = urlrequest.Request(
        urljoin(ALERTMANAGER_URL, "/api/v1/alerts"),
        data=payload.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urlrequest.urlopen(req, timeout=5)
    except Exception:
        pass


async def alert_if_needed(exc: Exception) -> None:
    """Send alert to AlertManager when error count reaches threshold."""
    error_counter.inc()
    current = error_counter._value.get()
    if ALERTMANAGER_URL and current % ERROR_ALERT_THRESHOLD == 0:
        payload = json.dumps(
            [
                {
                    "labels": {"alertname": "AuthServiceErrors"},
                    "annotations": {"summary": str(exc)},
                }
            ]
        )
        await asyncio.to_thread(_post_alert, payload)

