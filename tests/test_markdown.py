from datetime import date, time

from loop_calendar.db.models import EventModel, UserModel
from loop_calendar.domain.enums import EventKind
from loop_calendar.services.markdown import (
    MarkdownRenderer,
    format_date_range,
    month_bounds,
    week_bounds,
)


def make_user(
    user_id: str, username: str, display_name: str | None = None
) -> UserModel:
    return UserModel(id=user_id, username=username, display_name=display_name)


def make_event(
    *,
    event_id: int,
    user: UserModel,
    kind: EventKind,
    start_date: date,
    end_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    title: str | None = None,
) -> EventModel:
    event = EventModel(
        id=event_id,
        user_id=user.id,
        kind=kind,
        start_date=start_date,
        end_date=end_date or start_date,
        start_time=start_time,
        end_time=end_time,
        title=title,
    )
    event.user = user
    return event


def test_render_today_separates_statuses_and_meetings() -> None:
    renderer = MarkdownRenderer()
    kirill = make_user("u1", "kirill", "Кирилл")
    anna = make_user("u2", "anna", "Анна")
    target = date(2026, 8, 24)

    text = renderer.render_today(
        [
            make_event(
                event_id=1,
                user=kirill,
                kind=EventKind.REMOTE,
                start_date=target,
            ),
            make_event(
                event_id=2,
                user=anna,
                kind=EventKind.MEETING,
                start_date=target,
                start_time=time(14, 0),
                end_time=time(15, 0),
                title="Планерка",
            ),
        ],
        target_date=target,
    )

    assert "## Сегодня · 24 августа 2026" in text
    assert "🏠 **Кирилл** — удаленно" in text
    assert "14:00–15:00 — **Планерка** · Анна" in text


def test_render_today_empty_sections() -> None:
    text = MarkdownRenderer().render_today([], target_date=date(2026, 8, 24))

    assert "_Нет отмеченных статусов._" in text
    assert "_Нет встреч._" in text


def test_render_week_marks_status_and_multiple_meetings() -> None:
    renderer = MarkdownRenderer()
    kirill = make_user("u1", "kirill", "Кирилл")
    monday = date(2026, 8, 24)

    events = [
        make_event(
            event_id=1,
            user=kirill,
            kind=EventKind.SICK,
            start_date=monday,
        ),
        make_event(
            event_id=2,
            user=kirill,
            kind=EventKind.MEETING,
            start_date=monday,
            start_time=time(10, 0),
            end_time=time(11, 0),
            title="Первая",
        ),
        make_event(
            event_id=3,
            user=kirill,
            kind=EventKind.MEETING,
            start_date=monday,
            start_time=time(15, 0),
            end_time=time(16, 0),
            title="Вторая",
        ),
    ]

    text = renderer.render_week([kirill], events, start_date=monday)

    assert "| **Кирилл** | 🤒 📅×2 |" in text
    assert "**24 августа, понедельник**" in text
    assert "- 10:00–11:00 — **Первая** · Кирилл" in text
    assert "- 15:00–16:00 — **Вторая** · Кирилл" in text


def test_render_mine_contains_ids_and_delete_hint() -> None:
    renderer = MarkdownRenderer()
    user = make_user("u1", "kirill")

    text = renderer.render_mine(
        [
            make_event(
                event_id=7,
                user=user,
                kind=EventKind.DAY_OFF,
                start_date=date(2026, 8, 28),
            ),
            make_event(
                event_id=8,
                user=user,
                kind=EventKind.MEETING,
                start_date=date(2026, 8, 29),
                start_time=time(12, 0),
                end_time=time(13, 0),
                title="Созвон",
            ),
        ]
    )

    assert "`#7` 🛑" in text
    assert "`#8` 🤝" in text
    assert "Удалить событие: `/cal delete <id>`" in text


def test_render_created_and_deleted() -> None:
    renderer = MarkdownRenderer()
    user = make_user("u1", "kirill")
    event = make_event(
        event_id=42,
        user=user,
        kind=EventKind.SICK,
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 26),
    )

    created = renderer.render_created(event)
    deleted = renderer.render_deleted(event)

    assert "Больничный добавлено" in created
    assert "24–26 августа 2026" in created
    assert "`#42`" in created
    assert deleted == "✅ Событие `#42` удалено."


def test_date_bounds_helpers() -> None:
    assert week_bounds(date(2026, 8, 27)) == (
        date(2026, 8, 24),
        date(2026, 8, 30),
    )
    assert month_bounds(2028, 2) == (
        date(2028, 2, 1),
        date(2028, 2, 29),
    )


def test_format_date_range_same_month() -> None:
    user = make_user("u1", "kirill")
    event = make_event(
        event_id=1,
        user=user,
        kind=EventKind.VACATION,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 14),
    )

    assert format_date_range(event) == "1–14 сентября 2026"
