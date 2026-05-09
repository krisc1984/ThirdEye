from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "ai-tech-review-api"
    data_dir: Path = Path(__file__).resolve().parents[4] / "data"

    model_config = SettingsConfigDict(env_prefix="AI_REVIEW_")


settings = Settings()
