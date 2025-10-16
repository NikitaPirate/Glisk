"""Application configuration using Pydantic BaseSettings."""

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # PostgreSQL Database Configuration
    postgres_db: str = Field(default="glisk", alias="POSTGRES_DB")
    postgres_user: str = Field(default="glisk", alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    # Application Database Configuration
    database_url: str = Field(alias="DATABASE_URL")
    db_pool_size: int = Field(default=200, alias="DB_POOL_SIZE")

    # Application Environment
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # CORS Configuration
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


def configure_logging(settings: Settings) -> None:
    """Configure structlog based on application environment.

    - Production: JSON output for log aggregation
    - Development: Console output for human readability
    """
    if settings.app_env == "production":
        # JSON output for production (log aggregation)
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console output for development (human-readable)
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
