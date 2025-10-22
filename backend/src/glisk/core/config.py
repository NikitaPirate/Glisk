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

    # Replicate Image Generation (003-003c-image-generation)
    replicate_api_token: str = Field(default="", alias="REPLICATE_API_TOKEN")
    replicate_model_version: str = Field(
        default="black-forest-labs/flux-schnell", alias="REPLICATE_MODEL_VERSION"
    )
    fallback_censored_prompt: str = Field(
        default=(
            "Cute kittens and flowers in a peaceful garden, "
            "with text overlay saying 'Original prompt was censored by AI service'"
        ),
        alias="FALLBACK_CENSORED_PROMPT",
    )
    default_prompt: str = Field(
        default=(
            "Geometric patterns and vibrant colors with text saying "
            "'No prompt yet - author still thinking...'"
        ),
        alias="DEFAULT_PROMPT",
    )
    poll_interval_seconds: int = Field(default=1, alias="POLL_INTERVAL_SECONDS")
    worker_batch_size: int = Field(default=10, alias="WORKER_BATCH_SIZE")

    # IPFS Upload (Pinata) - 003-003d-ipfs-reveal
    pinata_jwt: str = Field(default="", alias="PINATA_JWT")
    pinata_gateway: str = Field(default="gateway.pinata.cloud", alias="PINATA_GATEWAY")

    # Blockchain Keeper - 003-003d-ipfs-reveal
    keeper_private_key: str = Field(default="", alias="KEEPER_PRIVATE_KEY")
    keeper_gas_strategy: str = Field(default="medium", alias="KEEPER_GAS_STRATEGY")
    reveal_gas_buffer: float = Field(default=1.2, alias="REVEAL_GAS_BUFFER")
    reveal_max_gas_price_gwei: float | None = Field(default=0.01, alias="REVEAL_MAX_GAS_PRICE_GWEI")
    transaction_timeout_seconds: int = Field(default=180, alias="TRANSACTION_TIMEOUT_SECONDS")

    # Reveal Worker - 003-003d-ipfs-reveal
    batch_reveal_wait_seconds: int = Field(default=5, alias="BATCH_REVEAL_WAIT_SECONDS")
    batch_reveal_max_tokens: int = Field(default=50, alias="BATCH_REVEAL_MAX_TOKENS")

    # Token Recovery - 004-recovery-1-nexttokenid
    recovery_batch_size: int = Field(default=1000, alias="RECOVERY_BATCH_SIZE")

    # X (Twitter) OAuth Integration - 007-link-x-twitter
    x_client_id: str = Field(default="", alias="X_CLIENT_ID")
    x_client_secret: str = Field(default="", alias="X_CLIENT_SECRET")
    x_redirect_uri: str = Field(
        default="http://localhost:8000/api/authors/x/callback", alias="X_REDIRECT_URI"
    )
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @model_validator(mode="after")
    def validate_required_config(self) -> "Settings":
        """Validate required configuration on startup.

        Ensures ALL required environment variables are set for the application to function.
        Fails fast with clear error messages if configuration is incomplete.

        Validation is skipped in test/development environments to avoid breaking tests.
        """
        # Skip validation in test environments
        if self.app_env in ("test", "testing"):
            return self

        # Collect all missing required variables
        missing = []

        # REPLICATE_API_TOKEN is required for image generation worker
        if not self.replicate_api_token:
            missing.append(
                "REPLICATE_API_TOKEN: Get your API token from https://replicate.com/account/api-tokens"
            )

        # PINATA_JWT is required for IPFS upload worker
        if not self.pinata_jwt:
            missing.append("PINATA_JWT: Get your JWT token from https://pinata.cloud")

        # KEEPER_PRIVATE_KEY is required for reveal worker
        if not self.keeper_private_key:
            missing.append("KEEPER_PRIVATE_KEY: Generate a keeper wallet and fund with ETH for gas")

        # GLISK_NFT_CONTRACT_ADDRESS is required for all workers
        if not self.glisk_nft_contract_address:
            missing.append("GLISK_NFT_CONTRACT_ADDRESS: Deploy contract or use existing address")

        # If any required variables are missing, fail fast
        if missing:
            error_msg = "CRITICAL: Missing required environment variables:\n\n" + "\n".join(
                f"  - {m}" for m in missing
            )
            error_msg += "\n\nThe application cannot start without these variables."
            error_msg += "\nPlease update your .env file and restart."
            raise ValueError(error_msg)

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
