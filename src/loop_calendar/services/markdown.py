import calendar
from datetime import date, timedelta

from loop_calendar.db.models import EventModel, UserModel
from loop_calendar.db.repository import CalendarRepository
from loop_calendar.domain.enums import (
    EVENT_EMOJI,
    EVENT_LABELS,
    EventKind,
)

_MONTHS = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_MONTHS_NOMINATIVE = (
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)

_WEEKDAYS_SHORT = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

_WEEKDAYS = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)


class MarkdownRenderer:
    def render_help(self) -> str:
        return """### 📅 Командный календарь

**Просмотр**
- `/cal today` — сегодня
- `/cal week` — текущая неделя
- `/cal mine` — ваши будущие события

**Статусы**
- `/cal remote tomorrow`
- `/cal remote 24.08-26.08`
- `/cal vacation 01.09–14.09`
- `/cal off 28.08`

**Встречи**
- `/cal meeting 25.08 14:00-15:00 "Редакционная планерка"`

**Удаление записей**
- `/cal delete 42`

Даты: `today`, `tomorrow`, `25.08`, `25.08.2026`, `2026-08-25`.

Диапазоны можно указывать через `..`, `-`, `–` или `—`.

Можно использовать русские алиасы:
`удаленка`, `удалёнка`, `отпуск`, `отгул`, `встреча`.
"""

    def render_today(
        self,
        events: list[EventModel],
        *,
        target_date: date,
    ) -> str:
        statuses = [
            event
            for event in events
            if event.kind != EventKind.MEETING
            and event.start_date <= target_date <= event.end_date
        ]

        meetings = [
            event
            for event in events
            if event.kind == EventKind.MEETING and event.start_date == target_date
        ]

        lines = [
            f"## Сегодня · {format_date(target_date)}",
            "",
            "### Статусы",
            "",
        ]

        if statuses:
            for event in sorted(
                statuses,
                key=lambda item: display_name(item.user).lower(),
            ):
                lines.append(
                    f"{EVENT_EMOJI[event.kind]} "
                    f"**{escape_md(display_name(event.user))}** "
                    f"— {EVENT_LABELS[event.kind]}"
                )
        else:
            lines.append("_Нет отмеченных статусов._")

        lines.extend(
            [
                "",
                "### Встречи",
                "",
            ]
        )

        if meetings:
            for event in sorted(
                meetings,
                key=lambda item: (
                    item.start_time,
                    item.id,
                ),
            ):
                owner = escape_md(display_name(event.user))
                title = escape_md(event.title or "Без названия")

                lines.append(f"{format_time_range(event)} — **{title}** · {owner}")
        else:
            lines.append("_Нет встреч._")

        return "\n".join(lines)

    def render_week(
        self,
        users: list[UserModel],
        events: list[EventModel],
        *,
        start_date: date,
    ) -> str:
        days = [start_date + timedelta(days=offset) for offset in range(7)]

        end_date = days[-1]

        header = ["Сотрудник"] + [
            f"{_WEEKDAYS_SHORT[day.weekday()]} {day.day}" for day in days
        ]

        lines = [
            "## 📅 Командный календарь",
            "",
            f"**{format_date(start_date)} — {format_date(end_date)}**",
            "",
            "| " + " | ".join(header) + " |",
            "|" + "|".join(["---"] + [":---:"] * 7) + "|",
        ]

        for user in sorted(
            users,
            key=lambda item: display_name(item).lower(),
        ):
            cells = [f"**{escape_table(display_name(user))}**"]

            user_events = [event for event in events if event.user_id == user.id]

            for day in days:
                parts: list[str] = []

                statuses = [
                    event
                    for event in user_events
                    if event.kind != EventKind.MEETING
                    and event.start_date <= day <= event.end_date
                ]

                if statuses:
                    parts.append(EVENT_EMOJI[statuses[0].kind])

                meeting_count = sum(
                    1
                    for event in user_events
                    if event.kind == EventKind.MEETING and event.start_date == day
                )

                if meeting_count == 1:
                    parts.append("📅")
                elif meeting_count > 1:
                    parts.append(f"📅×{meeting_count}")

                cells.append(" ".join(parts))

            lines.append("| " + " | ".join(cells) + " |")

        if not users:
            lines.append("| _Пока нет пользователей_ |  |  |  |  |  |  |  |")

        lines.extend(
            [
                "",
                "🏠 удаленно · 🌴 отпуск · 🟡 отгул · 📅 встреча",
            ]
        )

        meetings = [event for event in events if event.kind == EventKind.MEETING]

        lines.extend(
            [
                "",
                "### Встречи",
                "",
            ]
        )

        if not meetings:
            lines.append("_На этой неделе встреч нет._")
        else:
            current_day: date | None = None

            for event in sorted(
                meetings,
                key=lambda item: (
                    item.start_date,
                    item.start_time,
                    item.id,
                ),
            ):
                if event.start_date != current_day:
                    current_day = event.start_date

                    lines.extend(
                        [
                            "",
                            f"**{format_date_with_weekday(current_day)}**",
                            "",
                        ]
                    )

                title = escape_md(event.title or "Без названия")
                owner = escape_md(display_name(event.user))

                lines.append(f"- {format_time_range(event)} — **{title}** · {owner}")

        return "\n".join(lines)

    def render_mine(
        self,
        events: list[EventModel],
    ) -> str:
        lines = [
            "## Ваш календарь",
            "",
        ]

        if not events:
            lines.append("_Будущих событий нет._")
            return "\n".join(lines)

        for event in events:
            emoji = EVENT_EMOJI[event.kind]

            if event.kind == EventKind.MEETING:
                title = escape_md(event.title or "Без названия")

                lines.append(
                    f"- `#{event.id}` {emoji} "
                    f"**{format_date(event.start_date)}, "
                    f"{format_time_range(event)}** "
                    f"— {title}"
                )
            else:
                lines.append(
                    f"- `#{event.id}` {emoji} "
                    f"**{format_date_range(event)}** "
                    f"— {EVENT_LABELS[event.kind]}"
                )

        lines.extend(
            [
                "",
                "Удалить событие: `/cal delete <id>`",
            ]
        )

        return "\n".join(lines)

    def render_month(
        self,
        events: list[EventModel],
        *,
        year: int,
        month: int,
    ) -> str:
        lines = [
            f"# {_MONTHS_NOMINATIVE[month]} {year}",
            "",
        ]

        if not events:
            lines.append("_Событий нет._")
            return "\n".join(lines)

        first_day = date(year, month, 1)
        last_day = date(
            year,
            month,
            calendar.monthrange(year, month)[1],
        )

        day = first_day

        while day <= last_day:
            active = [
                event for event in events if event.start_date <= day <= event.end_date
            ]

            if active:
                lines.extend(
                    [
                        f"## {format_date_with_weekday(day)}",
                        "",
                    ]
                )

                for event in sorted(
                    active,
                    key=lambda item: (
                        item.kind is EventKind.MEETING,
                        display_name(item.user).lower(),
                        item.start_time,
                        item.id,
                    ),
                ):
                    owner = escape_md(display_name(event.user))
                    emoji = EVENT_EMOJI[event.kind]

                    if event.kind == EventKind.MEETING:
                        title = escape_md(event.title or "Без названия")

                        lines.append(
                            f"- {emoji} "
                            f"{format_time_range(event)} "
                            f"— **{title}** · {owner}"
                        )
                    else:
                        lines.append(
                            f"- {emoji} **{owner}** — {EVENT_LABELS[event.kind]}"
                        )

                lines.append("")

            day += timedelta(days=1)

        return "\n".join(lines).rstrip()

    def render_created(
        self,
        event: EventModel,
    ) -> str:
        if event.kind == EventKind.MEETING:
            return (
                "✅ **Встреча добавлена**\n\n"
                f"{format_date(event.start_date)}, "
                f"{format_time_range(event)}  \n"
                f"{escape_md(event.title or 'Без названия')}\n\n"
                f"ID события: `#{event.id}`"
            )

        return (
            f"✅ **{EVENT_LABELS[event.kind].capitalize()} добавлено**\n\n"
            f"{format_date_range(event)}\n\n"
            f"ID события: `#{event.id}`"
        )

    def render_deleted(
        self,
        event: EventModel,
    ) -> str:
        return f"✅ Событие `#{event.id}` удалено."


class MarkdownService:
    def __init__(
        self,
        repository: CalendarRepository,
        renderer: MarkdownRenderer,
    ) -> None:
        self.repository = repository
        self.renderer = renderer

    def render_help(self) -> str:
        return self.renderer.render_help()

    def render_today(
        self,
        *,
        target_date: date,
    ) -> str:
        events = self.repository.find_events(
            start_date=target_date,
            end_date=target_date,
        )

        return self.renderer.render_today(
            events,
            target_date=target_date,
        )

    def render_week(
        self,
        *,
        today: date,
    ) -> str:
        start_date, end_date = week_bounds(today)

        users = self.repository.list_users()

        events = self.repository.find_events(
            start_date=start_date,
            end_date=end_date,
        )

        return self.renderer.render_week(
            users,
            events,
            start_date=start_date,
        )

    def render_mine(
        self,
        *,
        user_id: str,
        from_date: date,
    ) -> str:
        events = self.repository.find_user_events(
            user_id=user_id,
            from_date=from_date,
        )

        return self.renderer.render_mine(events)

    def render_month(
        self,
        *,
        year: int,
        month: int,
    ) -> str:
        start_date, end_date = month_bounds(
            year,
            month,
        )

        events = self.repository.find_events(
            start_date=start_date,
            end_date=end_date,
        )

        return self.renderer.render_month(
            events,
            year=year,
            month=month,
        )


def week_bounds(
    value: date,
) -> tuple[date, date]:
    start = value - timedelta(days=value.weekday())

    return (
        start,
        start + timedelta(days=6),
    )


def month_bounds(
    year: int,
    month: int,
) -> tuple[date, date]:
    return (
        date(year, month, 1),
        date(
            year,
            month,
            calendar.monthrange(year, month)[1],
        ),
    )


def display_name(
    user: UserModel,
) -> str:
    return user.display_name or user.username


def format_date(
    value: date,
) -> str:
    return f"{value.day} {_MONTHS[value.month]} {value.year}"


def format_date_with_weekday(
    value: date,
) -> str:
    return f"{value.day} {_MONTHS[value.month]}, {_WEEKDAYS[value.weekday()]}"


def format_date_range(
    event: EventModel,
) -> str:
    if event.start_date == event.end_date:
        return format_date(event.start_date)

    if (
        event.start_date.year == event.end_date.year
        and event.start_date.month == event.end_date.month
    ):
        return (
            f"{event.start_date.day}–"
            f"{event.end_date.day} "
            f"{_MONTHS[event.start_date.month]} "
            f"{event.start_date.year}"
        )

    return f"{format_date(event.start_date)} — {format_date(event.end_date)}"


def format_time_range(
    event: EventModel,
) -> str:
    if event.start_time is None or event.end_time is None:
        return "время не указано"

    return f"{event.start_time:%H:%M}–{event.end_time:%H:%M}"


def escape_md(
    value: str,
) -> str:
    return value.replace("|", r"\|")


def escape_table(
    value: str,
) -> str:
    return escape_md(value).replace(
        "\n",
        " ",
    )
