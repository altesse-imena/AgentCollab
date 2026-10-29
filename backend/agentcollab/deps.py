"""Builds the shared objects (database engine, LLM client) from settings."""

from sqlalchemy import Engine

from .config import Settings
from .db import make_engine, make_recorder
from .llm import LLMClient
from .llm.providers import make_provider


class MissingAPIKey(RuntimeError):
    pass


def build(settings: Settings) -> tuple[Engine, LLMClient]:
    if not settings.api_key and settings.agentcollab_provider != "openai_compatible":
        env = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[
            settings.agentcollab_provider
        ]
        raise MissingAPIKey(f"{env} is not set (add it to backend/.env)")
    engine = make_engine(settings.database_url)
    provider = make_provider(
        settings.agentcollab_provider, settings.api_key, settings.agentcollab_base_url
    )
    return engine, LLMClient(provider, recorder=make_recorder(engine))
