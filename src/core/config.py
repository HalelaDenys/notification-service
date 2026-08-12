import logging
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DEFAULT_FORMAT = (
    "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
)
DATA_DIR = BASE_DIR / Path("data/uploads")
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "text/plain",
    "text/csv",
}


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


class TelegramConfig(BaseModel):
    bot_token: str = ""
    admin_chat_id: int
    admin_notify: bool = False


class SlackConfig(BaseModel):
    bot_token: str = ""
    error_channel_id: str
    error_notify: bool = False


class PostgresConfig(BaseModel):
    user: str
    password: str
    host: str = "localhost"
    port: int = 5432
    db: str

    @property
    def dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.db}"
        )


class DBConfig(BaseModel):
    naming_convention: ClassVar[dict] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    echo: bool = False

    postgres: PostgresConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env",),
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    redis: RedisConfig
    midd: MiddlewareConfig
    tg: TelegramConfig
    slack: SlackConfig
    logging: LoggingConfig = LoggingConfig()
    smtp: SMTPConfig = SMTPConfig()
    db: DBConfig


settings = Settings()
