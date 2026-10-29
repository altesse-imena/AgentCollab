"""Builds the shared objects (database, event log, agents' dependencies) from settings."""

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


def build_store(settings: Settings) -> tuple[Engine, EventLog]:
    """Database and event log. Needs no API key, so replays work without one."""
    engine = make_engine(settings.database_url)
    return engine, EventLog(engine)


def build_deps(settings: Settings, engine: Engine, events: EventLog) -> Deps:
    if not settings.api_key and settings.agentcollab_provider != "openai_compatible":
        env = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[
            settings.agentcollab_provider
        ]
        raise MissingAPIKey(f"{env} is not set (add it to backend/.env)")
    provider = make_provider(
        settings.agentcollab_provider, settings.api_key, settings.agentcollab_base_url
    )
    cache = DbResponseCache(engine) if settings.agentcollab_response_cache else None
    recorder = combine(make_recorder(engine), llm_call_recorder(events))
    return Deps(
        llm=LLMClient(provider, recorder=recorder, cache=cache),
        sandbox=DockerSandbox(),
        model_for=settings.model_for,
        context_limit_chars=settings.agentcollab_context_limit_chars,
    )


def build(settings: Settings) -> tuple[Engine, Deps, EventLog]:
    engine, events = build_store(settings)
    return engine, build_deps(settings, engine, events), events
