import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DEFAULT_FORMAT = (
    "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
)


class MiddlewareConfig(BaseModel):
    cors_allowed_origins: list[str] = [
        "http://localhost",
        "http://localhost:5173",
    ]


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @property
    def dsn(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class LoggingConfig(BaseModel):
    log_level: Literal[
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ] = "info"

    log_format: str = LOG_DEFAULT_FORMAT

    @property
    def log_level_value(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level.upper()]


class SMTPConfig(BaseModel):
    """
    Dev configuration. With test data for Maildev.
    To work with SMTP, use:
        SMTPS (implicit TLS):
            port 465
            use_tls=True
            start_tls=False
        STARTTLS (explicit upgrade)
            port 587
            use_tls=False
            start_tls=True
    """

    host: str = "localhost"  # dev host
    port: int = 1025  # dev port
    username: str | None = None
    password: str | None = None

    use_tls: bool = False
    start_tls: bool = True

    sender: str = "admin@example.com"
    timeout: float = 10.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env",),
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    redis: RedisConfig
    midd: MiddlewareConfig
    logging: LoggingConfig = LoggingConfig()
    smtp: SMTPConfig = SMTPConfig()


settings = Settings()
