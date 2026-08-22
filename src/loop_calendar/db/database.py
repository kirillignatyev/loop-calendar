from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from loop_calendar.config import get_settings
from loop_calendar.db.base import Base


class Database:
    def __init__(self, url: str) -> None:
        parsed = make_url(url)
        kwargs: dict[str, object] = {}

        if parsed.drivername.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}

            if parsed.database == ":memory:":
                kwargs["poolclass"] = StaticPool

        self.url = url
        self.engine = create_engine(url, **kwargs)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def _ensure_sqlite_parent(self) -> None:
        parsed = make_url(self.url)
        if not parsed.drivername.startswith("sqlite"):
            return
        database = parsed.database
        if not database or database == ":memory:":
            return

        Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def init(self) -> None:
        self._ensure_sqlite_parent()
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()


@lru_cache
def get_database() -> Database:
    return Database(get_settings().database_url)


def get_session(
    database: Annotated[Database, Depends(get_database)],
) -> Generator[Session, None, None]:
    with database.session() as session:
        yield session
