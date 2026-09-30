"""Settings from environment variables (A.10). No secrets, no .env file. Owner: T0."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KBC_", extra="ignore")

    cors_origins_raw: str = Field("http://localhost:3000", validation_alias="KBC_CORS_ORIGINS")
    demo_mode: bool = True  # KBC_DEMO_MODE: enables /reset and /scenarios
    max_body_bytes: int = 16 * 1024  # KBC_MAX_BODY_BYTES
    max_events_per_customer: int = 2000  # KBC_MAX_EVENTS_PER_CUSTOMER

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
