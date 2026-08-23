import re
import shlex
from datetime import date, datetime, time, timedelta

from .commands import (
    AddMeeting,
    AddStatus,
    CalendarCommand,
    DeleteEvent,
    ShowCalendar,
    ShowHelp,
)
from .enums import EventKind
from .errors import InvalidCommand

_KIND_ALIASES = {
    "remote": EventKind.REMOTE,
    "удаленка": EventKind.REMOTE,
    "удалёнка": EventKind.REMOTE,
    "vacation": EventKind.VACATION,
    "отпуск": EventKind.VACATION,
    "off": EventKind.DAY_OFF,
    "отгул": EventKind.DAY_OFF,
    "sick": EventKind.SICK,
    "больничный": EventKind.SICK,
    "болею": EventKind.SICK,
}

_VIEW_ALIASES = {
    "today": "today",
    "сегодня": "today",
    "tomorrow": "tomorrow",
    "завтра": "tomorrow",
    "week": "week",
    "неделя": "week",
    "mine": "mine",
    "me": "mine",
    "мой": "mine",
    "мои": "mine",
    "я": "mine",
}

_MEETING_ALIASES = {
    "meeting",
    "встреча",
    "собрание",
    "совещание",
}

_DELETE_ALIASES = {
    "delete",
    "удалить",
    "remove",
    "cancel",
    "отменить",
    "отмена",
}

_HELP_ALIASES = {"help", "помощь"}

_DAY_MONTH_RE = re.compile(r"^(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.?$")

_DAY_MONTH_YEAR_RE = re.compile(
    r"^(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})$"
)

_DATE_RANGE_RE = re.compile(r"^(?P<start>.+?)\s*(?:\.\.|[-–—])\s*(?P<end>.+?)$")

_TIME_RANGE_RE = re.compile(
    r"^(?P<start>\d{1,2}:\d{2})\s*[-–—]\s*(?P<end>\d{1,2}:\d{2})$"
)


def parse_command(text: str, *, today: date) -> CalendarCommand:
    try:
        parts = shlex.split(text.strip())
    except ValueError as exc:
        raise InvalidCommand("Не удалось разобрать кавычки в команде.") from exc

    if not parts:
        return ShowHelp()

    action = parts[0].lower()

    if action in _HELP_ALIASES:
        _require_count(parts, 1, "Использование: /cal help")
        return ShowHelp()

    if action in _VIEW_ALIASES:
        _require_count(parts, 1, f"Использование: /cal {action}")
        return ShowCalendar(scope=_VIEW_ALIASES[action])

    if action in _DELETE_ALIASES:
        _require_count(parts, 2, "Использование: /cal delete <id>")
        try:
            event_id = int(parts[1])
        except ValueError as exc:
            raise InvalidCommand("ID события должен быть целым числом.") from exc

        if event_id <= 0:
            raise InvalidCommand("ID события должен быть положительным числом.")

        return DeleteEvent(event_id=event_id)

    if action in _KIND_ALIASES:
        _require_count(parts, 2, f"Использование: /cal {action} <дата или диапазон>")
        start_date, end_date = parse_date_range(parts[1], today=today)
        return AddStatus(
            kind=_KIND_ALIASES[action],
            start_date=start_date,
            end_date=end_date,
        )

    if action in _MEETING_ALIASES:
        if len(parts) < 4:
            raise InvalidCommand(
                'Использование: /cal meeting <дата> <HH:MM–HH:MM> "Название встречи"'
            )

        meeting_date = parse_date(parts[1], today=today)
        start_time, end_time = parse_time_range(parts[2])
        title = " ".join(parts[3:]).strip()

        if not title:
            raise InvalidCommand("У встречи должно быть название.")

        return AddMeeting(
            date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            title=title,
        )


def _require_count(parts: list[str], expected: int, usage: str) -> None:
    if len(parts) != expected:
        raise InvalidCommand(usage)


def parse_date(
    value: str,
    *,
    today: date,
    default_year: int | None = None,
) -> date:
    normalized = value.lower()

    if normalized in {"today", "сегодня"}:
        return today

    if normalized in {"tomorrow", "завтра"}:
        return today + timedelta(days=1)

    try:
        return date.fromisoformat(value)
    except ValueError:
        pass

    match = _DAY_MONTH_YEAR_RE.fullmatch(value)
    if match:
        return _make_date(
            int(match["year"]),
            int(match["month"]),
            int(match["day"]),
        )

    match = _DAY_MONTH_RE.fullmatch(value)
    if match:
        return _make_date(
            default_year or today.year,
            int(match["month"]),
            int(match["day"]),
        )

    raise InvalidCommand(
        f"Не удалось распознать дату `{value}`. Используйте:\n"
        "• `today`\n• `tomorrow`\n• `25.08`\n• `25.08.2026`\n• `2026-08-25`"
    )


def _make_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise InvalidCommand(
            f"Некорректная дата: {day:02d}.{month:02d}.{year}"
        ) from exc


def _is_day_month(value: str) -> bool:
    return _DAY_MONTH_RE.fullmatch(value) is not None


def parse_date_range(value: str, *, today: date) -> tuple[date, date]:
    try:
        parsed = parse_date(value, today=today)
    except InvalidCommand:
        pass
    else:
        return parsed, parsed

    match = _DATE_RANGE_RE.fullmatch(value)
    if match is None:
        raise InvalidCommand(
            "Диапазон должен иметь вид `24.08..26.08`, "
            "`24.08-26.08`, `24.08–26.08` или `24.08—26.08`."
        )

    start_raw = match["start"].strip()
    end_raw = match["end"].strip()

    start_date = parse_date(start_raw, today=today)
    end_date = parse_date(
        end_raw,
        today=today,
        default_year=start_date.year,
    )

    if _is_day_month(end_raw) and end_date < start_date:
        try:
            end_date = end_date.replace(year=end_date.year + 1)
        except ValueError as exc:
            raise InvalidCommand("Некорректная конечная дата диапазона.") from exc
    if end_date < start_date:
        raise InvalidCommand("Конец диапазона не может быть раньше начала.")

    return start_date, end_date


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise InvalidCommand(f"Некорректное время `{value}`.") from exc


def parse_time_range(value: str) -> tuple[time, time]:
    match = _TIME_RANGE_RE.fullmatch(value)

    if not match:
        raise InvalidCommand(
            "Время должно иметь вид `14:00-15:00`, `14:00–15:00` или `14:00—15:00`."
        )

    start = _parse_time(match["start"])
    end = _parse_time(match["end"])

    if end <= start:
        raise InvalidCommand("Конец встречи должен быть позже ее начала.")
    return start, end
