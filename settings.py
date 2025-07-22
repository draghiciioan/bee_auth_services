from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Simple configuration container loaded from environment variables."""

    def __init__(self) -> None:
        self.password_regex: str = os.getenv(
            "PASSWORD_REGEX",
            r"^(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
