from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from loop_calendar.db.database import Database
from loop_calendar.db.repository import CalendarRepository


@pytest.fixture
def database() -> Database:
    database = Database("sqlite:///:memory:")
    database.init()
    return database


@pytest.fixture
def session(database: Database) -> Generator[Session, None, None]:
    with database.session() as session:
        yield session


@pytest.fixture
def repository(session: Session) -> CalendarRepository:
    return CalendarRepository(session)
