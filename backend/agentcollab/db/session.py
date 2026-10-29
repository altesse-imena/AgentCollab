from dataclasses import asdict

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from ..llm.client import CallRecord
from .models import Base, LLMCall


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
