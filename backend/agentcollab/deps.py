"""Builds the shared objects (database engine, LLM client) from settings."""

from sqlalchemy import Engine

from .config import Settings
from .db import DbResponseCache, make_engine, make_recorder
from .events import EventLog, combine, llm_call_recorder
from .graph import Deps
from .llm import LLMClient
from .llm.providers import make_provider
from .sandbox import DockerSandbox


class MissingAPIKey(RuntimeError):
    pass


def build(settings: Settings) -> tuple[Engine, Deps, EventLog]:
    if not settings.api_key and settings.agentcollab_provider != "openai_compatible":
        env = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[
            settings.agentcollab_provider
        ]
        raise MissingAPIKey(f"{env} is not set (add it to backend/.env)")
    engine = make_engine(settings.database_url)
    provider = make_provider(
        settings.agentcollab_provider, settings.api_key, settings.agentcollab_base_url
    )
    cache = DbResponseCache(engine) if settings.agentcollab_response_cache else None
    events = EventLog(engine)
    recorder = combine(make_recorder(engine), llm_call_recorder(events))
    llm = LLMClient(provider, recorder=recorder, cache=cache)
    deps = Deps(
        llm=llm,
        sandbox=DockerSandbox(),
        model_for=settings.model_for,
        context_limit_chars=settings.agentcollab_context_limit_chars,
    )
    return engine, deps, events
