"""Saves workflow progress after every step so a crashed run can resume where it stopped."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import make_url


@contextmanager
def open_checkpointer(database_url: str) -> Iterator[object]:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(url.database or ":memory:") as saver:
            yield saver
    elif url.get_backend_name() == "postgresql":
        from langgraph.checkpoint.postgres import PostgresSaver

        plain = url.set(drivername="postgresql").render_as_string(hide_password=False)
        with PostgresSaver.from_conn_string(plain) as saver:
            saver.setup()
            yield saver
    else:
        raise ValueError(f"no checkpointer for {url.get_backend_name()}")
