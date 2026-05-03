from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings, frozen=True):
    url: str = "postgresql+asyncpg://pinky:pinky@localhost:5432/pinky"


class RedisConfig(BaseSettings, frozen=True):
    url: str = "redis://localhost:6379/0"


class AuthConfig(BaseSettings, frozen=True):
    session_idle_timeout_minutes: int = 30
    session_absolute_timeout_hours: int = 8
    csrf_enabled: bool = True
    callback_base_url: str = "http://localhost:8000"
    openshift_issuer_url: str = ""
    openshift_client_id: str = ""
    openshift_client_secret: str = ""
    openshift_api_url: str = ""
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    cookie_domain: str = ""
    app_url: str = "http://localhost:3000"


class PinkySettings(BaseSettings, frozen=True):
    model_config = {"env_prefix": "PINKY_", "env_nested_delimiter": "__"}

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "json"


_settings: PinkySettings | None = None


def get_settings() -> PinkySettings:
    global _settings
    if _settings is None:
        _settings = PinkySettings()
    return _settings
