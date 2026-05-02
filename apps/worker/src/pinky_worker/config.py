from pydantic import Field
from pydantic_settings import BaseSettings


class TemporalConfig(BaseSettings, frozen=True):
    address: str = "localhost:7233"
    namespace: str = "pinky"


class WorkerConfig(BaseSettings, frozen=True):
    model_config = {"env_prefix": "PINKY_"}

    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    log_level: str = "INFO"


_settings: WorkerConfig | None = None


def get_settings() -> WorkerConfig:
    global _settings
    if _settings is None:
        _settings = WorkerConfig()
    return _settings
