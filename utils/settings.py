from __future__ import annotations

import os


class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        env = os.getenv
        self.environment: str | None = env("ENVIRONMENT")
        self.database_url: str = env(
            "DATABASE_URL", "postgresql://user:password@postgres-auth/auth"
        )
        self.secret_key: str = env("SECRET_KEY", "secret")
        self.jwt_algorithm: str = env("JWT_ALGORITHM", "HS256")
        self.token_expiration_seconds: int = int(
            env("TOKEN_EXPIRATION_SECONDS", "7200")
        )
        self.rsa_private_key_path: str | None = env("RSA_PRIVATE_KEY_PATH")
        self.rsa_public_key_path: str | None = env("RSA_PUBLIC_KEY_PATH")

        self.redis_host: str = env("REDIS_HOST", "redis")
        self.redis_port: int = int(env("REDIS_PORT", "6379"))
        self.redis_db: int = int(env("REDIS_DB", "0"))
        self.redis_password: str | None = env("REDIS_PASSWORD")

        self.rabbitmq_url: str = env("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
        self.sentry_dsn: str | None = env("SENTRY_DSN")
        self.cors_origins: str | None = env("CORS_ORIGINS")
        self.enable_metrics: bool = env("ENABLE_METRICS", "false").lower() in {
            "1",
            "true",
            "yes",
        }

        self.alertmanager_url: str | None = env("ALERTMANAGER_URL")
        self.error_alert_threshold: int = int(env("ERROR_ALERT_THRESHOLD", "10"))

        self.google_client_id: str | None = env("GOOGLE_CLIENT_ID")
        self.google_client_secret: str | None = env("GOOGLE_CLIENT_SECRET")
        self.google_redirect_uri: str | None = env("GOOGLE_REDIRECT_URI")
        self.facebook_client_id: str | None = env("FACEBOOK_CLIENT_ID")
        self.facebook_client_secret: str | None = env("FACEBOOK_CLIENT_SECRET")
        self.facebook_redirect_uri: str | None = env("FACEBOOK_REDIRECT_URI")

        self.password_regex: str = env(
            "PASSWORD_REGEX", r"^(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
