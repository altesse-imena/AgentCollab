from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

ROLES = ("writer", "reviewer", "tester", "security")

# Default model per provider. Override any role with AGENTCOLLAB_MODEL_<ROLE>.
DEFAULT_MODELS = {
    "openai": "gpt-4.1",
    "anthropic": "claude-opus-5-5",
    "openai_compatible": None,  # no sensible default; set AGENTCOLLAB_MODEL
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agentcollab_provider: str = "openai"
    agentcollab_base_url: str | None = None  # for openai_compatible
    agentcollab_model: str | None = None  # default model for every role
    agentcollab_model_writer: str | None = None
    agentcollab_model_reviewer: str | None = None
    agentcollab_model_tester: str | None = None
    agentcollab_model_security: str | None = None

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    agentcollab_api_key: str | None = None  # for openai_compatible

    # Cost optimizations; each can be switched off to measure it against a baseline
    agentcollab_response_cache: bool = False

    database_url: str = "sqlite:///./agentcollab.db"
    agentcollab_run_budget_usd: float = 0.50

    @property
    def api_key(self) -> str | None:
        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "openai_compatible": self.agentcollab_api_key,
        }.get(self.agentcollab_provider)

    def model_for(self, role: str) -> str:
        model = (
            getattr(self, f"agentcollab_model_{role}")
            or self.agentcollab_model
            or DEFAULT_MODELS.get(self.agentcollab_provider)
        )
        if not model:
            raise ValueError(f"no model configured for {role}; set AGENTCOLLAB_MODEL")
        return model


@lru_cache
def get_settings() -> Settings:
    return Settings()
