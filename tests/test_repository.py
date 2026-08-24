from datetime import date, time

from loop_calendar.db.models import EventModel
from loop_calendar.db.repository import CalendarRepository
from loop_calendar.domain.enums import EventKind


def test_get_or_create_user_creates_and_updates_username(
    repository: CalendarRepository,
) -> None:
    user = repository.get_or_create_user(user_id="u1", username="kirill")
    repository.commit()

    assert user.id == "u1"
    assert user.username == "kirill"

    same_user = repository.get_or_create_user(user_id="u1", username="k.ignatyev")
    repository.commit()

    assert same_user.id == "u1"
    assert same_user.username == "k.ignatyev"
    assert len(repository.list_users()) == 1


def test_find_events_returns_events_overlapping_requested_period(
    repository: CalendarRepository,
) -> None:
    repository.get_or_create_user(user_id="u1", username="kirill")
    inside = repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.REMOTE,
            start_date=date(2026, 8, 24),
            end_date=date(2026, 8, 26),
        )
    )
    outside = repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.VACATION,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 5),
        )
    )
    repository.commit()

    events = repository.find_events(
        start_date=date(2026, 8, 25),
        end_date=date(2026, 8, 31),
    )

    assert [event.id for event in events] == [inside.id]
    assert outside.id not in {event.id for event in events}
    assert events[0].user.username == "kirill"


def test_find_user_events_filters_past_events_and_orders_results(
    repository: CalendarRepository,
) -> None:
    repository.get_or_create_user(user_id="u1", username="kirill")
    repository.get_or_create_user(user_id="u2", username="anna")

    repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.REMOTE,
            start_date=date(2026, 8, 20),
            end_date=date(2026, 8, 20),
        )
    )
    second = repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.MEETING,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 25),
            start_time=time(15, 0),
            end_time=time(16, 0),
            title="Вторая",
        )
    )
    first = repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.MEETING,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 25),
            start_time=time(10, 0),
            end_time=time(11, 0),
            title="Первая",
        )
    )
    repository.add_event(
        EventModel(
            user_id="u2",
            kind=EventKind.VACATION,
            start_date=date(2026, 8, 24),
            end_date=date(2026, 8, 30),
        )
    )
    repository.commit()

    events = repository.find_user_events(
        user_id="u1",
        from_date=date(2026, 8, 24),
    )

    assert [event.id for event in events] == [first.id, second.id]


def test_status_conflicts_ignore_meetings(
    repository: CalendarRepository,
) -> None:
    repository.get_or_create_user(user_id="u1", username="kirill")
    status = repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.SICK,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 26),
        )
    )
    repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.MEETING,
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 25),
            start_time=time(10, 0),
            end_time=time(11, 0),
            title="Планерка",
        )
    )
    repository.commit()

    conflicts = repository.find_status_conflicts(
        user_id="u1",
        start_date=date(2026, 8, 26),
        end_date=date(2026, 8, 27),
    )

    assert [event.id for event in conflicts] == [status.id]


def test_delete_event_removes_row(repository: CalendarRepository) -> None:
    repository.get_or_create_user(user_id="u1", username="kirill")
    event = repository.add_event(
        EventModel(
            user_id="u1",
            kind=EventKind.DAY_OFF,
            start_date=date(2026, 8, 28),
            end_date=date(2026, 8, 28),
        )
    )
    repository.commit()

    repository.delete_event(event.id)
    repository.commit()

    assert repository.get_event(event.id) is None
