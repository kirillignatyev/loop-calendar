from datetime import date, time

import pytest

from loop_calendar.db.repository import CalendarRepository
from loop_calendar.domain.commands import AddMeeting, AddStatus
from loop_calendar.domain.enums import EventKind
from loop_calendar.domain.errors import EventConflict, EventNotFound, PermissionDenied
from loop_calendar.services.calendar import CalendarService


def test_add_status_creates_user_and_event(repository: CalendarRepository) -> None:
    service = CalendarService(repository)

    event = service.add_status(
        user_id="u1",
        username="kirill",
        command=AddStatus(
            kind=EventKind.REMOTE,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 26),
        ),
    )

    assert event.id is not None
    assert event.kind == EventKind.REMOTE
    assert repository.get_user("u1") is not None
    assert repository.get_event(event.id) is not None


def test_overlapping_status_for_same_user_is_rejected(
    repository: CalendarRepository,
) -> None:
    service = CalendarService(repository)
    service.add_status(
        user_id="u1",
        username="kirill",
        command=AddStatus(
            kind=EventKind.VACATION,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 30),
        ),
    )

    with pytest.raises(EventConflict, match="пересекающийся статус"):
        service.add_status(
            user_id="u1",
            username="kirill",
            command=AddStatus(
                kind=EventKind.SICK,
                start_date=date(2026, 8, 30),
                end_date=date(2026, 8, 31),
            ),
        )


def test_same_dates_are_allowed_for_different_users(
    repository: CalendarRepository,
) -> None:
    service = CalendarService(repository)
    command = AddStatus(
        kind=EventKind.REMOTE,
        start_date=date(2026, 8, 25),
        end_date=date(2026, 8, 25),
    )

    first = service.add_status(user_id="u1", username="kirill", command=command)
    second = service.add_status(user_id="u2", username="anna", command=command)

    assert first.id != second.id


def test_meeting_can_overlap_status(repository: CalendarRepository) -> None:
    service = CalendarService(repository)
    service.add_status(
        user_id="u1",
        username="kirill",
        command=AddStatus(
            kind=EventKind.REMOTE,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 25),
        ),
    )

    meeting = service.add_meeting(
        user_id="u1",
        username="kirill",
        command=AddMeeting(
            date=date(2026, 8, 25),
            start_time=time(14, 0),
            end_time=time(15, 0),
            title="Планерка",
        ),
    )

    assert meeting.kind == EventKind.MEETING
    assert meeting.title == "Планерка"


def test_delete_own_event(repository: CalendarRepository) -> None:
    service = CalendarService(repository)
    event = service.add_status(
        user_id="u1",
        username="kirill",
        command=AddStatus(
            kind=EventKind.DAY_OFF,
            start_date=date(2026, 8, 28),
            end_date=date(2026, 8, 28),
        ),
    )

    deleted = service.delete_event(event_id=event.id, user_id="u1")

    assert deleted.id == event.id
    assert repository.get_event(event.id) is None


def test_delete_foreign_event_is_forbidden(repository: CalendarRepository) -> None:
    service = CalendarService(repository)
    event = service.add_status(
        user_id="u1",
        username="kirill",
        command=AddStatus(
            kind=EventKind.DAY_OFF,
            start_date=date(2026, 8, 28),
            end_date=date(2026, 8, 28),
        ),
    )

    with pytest.raises(PermissionDenied):
        service.delete_event(event_id=event.id, user_id="u2")

    assert repository.get_event(event.id) is not None


def test_delete_unknown_event(repository: CalendarRepository) -> None:
    service = CalendarService(repository)

    with pytest.raises(EventNotFound, match="#999"):
        service.delete_event(event_id=999, user_id="u1")
