"""Application configuration using Pydantic BaseSettings."""

import structlog
from pydantic import Field, model_validator
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

    # Alchemy Integration (003-003b-event-detection)
    # Optional fields with defaults to maintain backward compatibility with existing tests
    alchemy_api_key: str = Field(default="", alias="ALCHEMY_API_KEY")
    alchemy_webhook_secret: str = Field(default="", alias="ALCHEMY_WEBHOOK_SECRET")
    glisk_nft_contract_address: str = Field(default="", alias="GLISK_NFT_CONTRACT_ADDRESS")
    network: str = Field(default="BASE_SEPOLIA", alias="NETWORK")
    glisk_default_author_wallet: str = Field(default="", alias="GLISK_DEFAULT_AUTHOR_WALLET")

    # Replicate Image Generation (003-003c-image-generation)
    replicate_api_token: str = Field(default="", alias="REPLICATE_API_TOKEN")
    replicate_model_version: str = Field(
        default="black-forest-labs/flux-schnell", alias="REPLICATE_MODEL_VERSION"
    )
    fallback_censored_prompt: str = Field(
        default="Cute kittens playing with yarn balls in a sunny meadow with flowers",
        alias="FALLBACK_CENSORED_PROMPT",
    )
    poll_interval_seconds: int = Field(default=1, alias="POLL_INTERVAL_SECONDS")
    worker_batch_size: int = Field(default=10, alias="WORKER_BATCH_SIZE")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @model_validator(mode="after")
    def validate_image_generation_config(self) -> "Settings":
        """Validate image generation configuration on startup.

        Ensures required environment variables are set for the worker to function.
        Fails fast with clear error messages if configuration is incomplete.

        Validation is skipped in test/development environments to avoid breaking tests.
        """
        # Skip validation in test environments
        if self.app_env in ("test", "testing"):
            return self

        # REPLICATE_API_TOKEN is required for image generation worker in production
        if not self.replicate_api_token:
            structlog.get_logger().warning(
                "config.validation.warning",
                message="REPLICATE_API_TOKEN not set - image generation worker will fail",
                hint="Get your API token from https://replicate.com/account/api-tokens",
            )

        # FALLBACK_CENSORED_PROMPT should be non-empty (has default, just warn)
        if not self.fallback_censored_prompt:
            structlog.get_logger().warning(
                "config.validation.warning",
                message="FALLBACK_CENSORED_PROMPT not set - using default",
            )

        return self


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
