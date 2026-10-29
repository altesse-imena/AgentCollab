from dataclasses import asdict

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from ..llm.client import CallRecord
from .models import Base, CachedResponse, LLMCall


def make_engine(url: str) -> Engine:
    engine = create_engine(url)
    # Alembic migrations come in week 3; until then create tables directly
    Base.metadata.create_all(engine)
    return engine


def make_recorder(engine: Engine):
    """Return a callback that writes each LLM call to llm_calls as soon as it finishes."""

    def record(call: CallRecord) -> None:
        with Session(engine) as s:
            s.add(LLMCall(**asdict(call)))
            s.commit()

    return record


class DbResponseCache:
    def __init__(self, engine: Engine):
        self.engine = engine

    def get(self, key: str) -> str | None:
        with Session(self.engine) as s:
            row = s.get(CachedResponse, key)
            return row.text if row else None

    def set(self, key: str, model: str, text: str) -> None:
        with Session(self.engine) as s:
            s.merge(CachedResponse(key=key, model=model, text=text))
            s.commit()
