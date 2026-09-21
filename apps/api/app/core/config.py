"""
PayGuard AI — Application Settings
Loaded from environment variables via pydantic-settings.
All secrets come from env / secret manager — never hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "InvarPay AI"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "info"
    secret_key: SecretStr = SecretStr("change-me-in-production")
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    # Database
    database_url: str = "postgresql+asyncpg://payguard:payguard_dev@localhost:5432/payguard"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: SecretStr = SecretStr("change-me-jwt-secret")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    api_key_prefix: str = "pg_live_"
    api_key_test_prefix: str = "pg_test_"

    # Payment providers
    payment_provider: Literal["fake", "razorpay_test"] = "fake"
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")
    razorpay_webhook_secret: SecretStr = SecretStr("")

    # LLM / AI
    openai_api_key: SecretStr = SecretStr("")
    google_api_key: SecretStr = SecretStr("")
    llm_provider: Literal["openai", "google", "fixture"] = "fixture"
    llm_model: str = "gpt-4o-mini"
    agent_max_iterations: int = 10
    agent_timeout_seconds: int = 30

    # Object storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: SecretStr = SecretStr("minioadmin")
    s3_bucket_reports: str = "invarpay-reports"
    s3_region: str = "us-east-1"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "invarpay-api"

    # Feature flags (all five modules enabled)
    feature_paymentgraph: bool = True
    feature_paydev: bool = True
    feature_merchantos: bool = True
    feature_shopagent: bool = True
    feature_mcp: bool = True

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Webhook security
    webhook_replay_window_seconds: int = 300
    webhook_max_payload_bytes: int = 1_048_576  # 1 MB

    # Demo / seed
    seed_demo_data: bool = True
    demo_org_name: str = "Demo Merchant Inc."

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def llm_configured(self) -> bool:
        """Returns True if at least one LLM API key is set."""
        return bool(
            self.openai_api_key.get_secret_value()
            or self.google_api_key.get_secret_value()
        )

    @property
    def razorpay_configured(self) -> bool:
        """Returns True if Razorpay test-mode credentials are configured."""
        return bool(self.razorpay_key_id and self.razorpay_key_secret.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Call this everywhere instead of Settings()."""
    return Settings()
