from datetime import date, time

import pytest

from loop_calendar.domain.commands import (
    AddMeeting,
    AddStatus,
    DeleteEvent,
    ShowCalendar,
    ShowHelp,
)
from loop_calendar.domain.enums import EventKind
from loop_calendar.domain.errors import InvalidCommand
from loop_calendar.domain.parser import (
    parse_command,
    parse_date,
    parse_date_range,
    parse_time_range,
)

TODAY = date(2026, 8, 24)


def test_empty_command_shows_help() -> None:
    assert parse_command("", today=TODAY) == ShowHelp()


@pytest.mark.parametrize("command", ["help", "помощь"])
def test_help_aliases(command: str) -> None:
    assert parse_command(command, today=TODAY) == ShowHelp()


@pytest.mark.parametrize(
    ("command", "scope"),
    [
        ("today", "today"),
        ("сегодня", "today"),
        ("week", "week"),
        ("неделя", "week"),
        ("mine", "mine"),
        ("me", "mine"),
        ("мой", "mine"),
        ("мои", "mine"),
        ("я", "mine"),
    ],
)
def test_calendar_view_aliases(command: str, scope: str) -> None:
    assert parse_command(command, today=TODAY) == ShowCalendar(scope=scope)


@pytest.mark.parametrize(
    ("command", "kind"),
    [
        ("remote tomorrow", EventKind.REMOTE),
        ("удаленка tomorrow", EventKind.REMOTE),
        ("удалёнка tomorrow", EventKind.REMOTE),
        ("vacation tomorrow", EventKind.VACATION),
        ("отпуск tomorrow", EventKind.VACATION),
        ("off tomorrow", EventKind.DAY_OFF),
        ("отгул tomorrow", EventKind.DAY_OFF),
        ("sick tomorrow", EventKind.SICK),
        ("больничный tomorrow", EventKind.SICK),
        ("болею tomorrow", EventKind.SICK),
    ],
)
def test_status_aliases(command: str, kind: EventKind) -> None:
    assert parse_command(command, today=TODAY) == AddStatus(
        kind=kind,
        start_date=date(2026, 8, 25),
        end_date=date(2026, 8, 25),
    )


def test_status_date_range() -> None:
    assert parse_command("vacation 25.08-31.08", today=TODAY) == AddStatus(
        kind=EventKind.VACATION,
        start_date=date(2026, 8, 25),
        end_date=date(2026, 8, 31),
    )


def test_day_month_range_can_cross_year_boundary() -> None:
    assert parse_date_range("30.12-02.01", today=TODAY) == (
        date(2026, 12, 30),
        date(2027, 1, 2),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("today", date(2026, 8, 24)),
        ("сегодня", date(2026, 8, 24)),
        ("tomorrow", date(2026, 8, 25)),
        ("завтра", date(2026, 8, 25)),
        ("25.08", date(2026, 8, 25)),
        ("25.08.", date(2026, 8, 25)),
        ("25.08.2027", date(2027, 8, 25)),
        ("2027-08-25", date(2027, 8, 25)),
    ],
)
def test_parse_date(raw: str, expected: date) -> None:
    assert parse_date(raw, today=TODAY) == expected


@pytest.mark.parametrize("separator", ["-", "–", "—"])
def test_meeting_time_separators(separator: str) -> None:
    command = parse_command(
        f'встреча 25.08 14:00{separator}15:30 "Редакционная планерка"',
        today=TODAY,
    )

    assert command == AddMeeting(
        date=date(2026, 8, 25),
        start_time=time(14, 0),
        end_time=time(15, 30),
        title="Редакционная планерка",
    )


@pytest.mark.parametrize("command", ["meeting", "встреча", "собрание", "совещание"])
def test_meeting_aliases(command: str) -> None:
    parsed = parse_command(
        f'{command} 25.08 10:00-11:00 "Планерка"',
        today=TODAY,
    )
    assert isinstance(parsed, AddMeeting)
    assert parsed.title == "Планерка"


@pytest.mark.parametrize(
    "command",
    ["delete 42", "удалить 42", "remove 42", "cancel 42", "отменить 42"],
)
def test_delete_aliases(command: str) -> None:
    assert parse_command(command, today=TODAY) == DeleteEvent(event_id=42)


@pytest.mark.parametrize(
    "command",
    [
        "unknown",
        "tomorrow",
        "delete 0",
        "delete abc",
        "remote",
        "remote 31.02",
        "meeting 25.08 15:00-14:00 Планерка",
        "meeting 25.08 wrong-time Планерка",
        'meeting 25.08 14:00-15:00 "незакрытая кавычка',
    ],
)
def test_invalid_commands_raise_user_facing_error(command: str) -> None:
    with pytest.raises(InvalidCommand):
        parse_command(command, today=TODAY)


def test_invalid_time_range() -> None:
    with pytest.raises(InvalidCommand, match="позже"):
        parse_time_range("14:00-14:00")
