from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    openai_api_key: str | None = None
    database_url: str = "sqlite:///./agentcollab.db"
    agentcollab_writer_model: str = "gpt-4.1"
    agentcollab_run_budget_usd: float = 0.50


@lru_cache
def get_settings() -> Settings:
    return Settings()
