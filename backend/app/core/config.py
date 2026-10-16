"""
Centralized, environment-driven configuration.

Every other module reads settings from here rather than calling os.getenv
directly, so there is exactly one place that defines what env vars exist
and what their defaults/types are.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "ComplianceNavigator AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Security
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # Database
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "compliance_navigator"
    # How long to wait for Mongo to respond before giving up and falling
    # back to sample data (see db/mongo.py). Localhost typically responds
    # in well under a second; a cloud database like Atlas has real network
    # round-trip + TLS handshake time on top of that, so this defaults
    # higher than a bare-minimum localhost value would need.
    mongo_timeout_ms: int = 8000

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Crawler (Phase 2)
    crawler_user_agent: str = "ComplianceNavigatorBot/1.0 (+contact: compliance@yourorg.com)"
    crawler_interval_hours: int = 24
    # Automatic self-updating. When true (the default) the API server runs
    # the crawler on a timer in-process and rebuilds the search index after
    # every pass, so documents stay current with no manual steps. Set to
    # false if you prefer to drive crawls from cron / GitHub Actions.
    crawler_autostart: bool = True
    # Grace period before the first automatic crawl, so the server is up and
    # answering requests before it starts hitting external sites.
    crawler_startup_delay_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CN_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
