import logging
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with optional contextual fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for field in ("user_id", "ip", "endpoint"):
            if hasattr(record, field):
                log_record[field] = getattr(record, field)
        return json.dumps(log_record)


def configure_logging() -> None:
    """Configure root logger to output JSON formatted logs to stdout."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

