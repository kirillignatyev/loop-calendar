from enum import StrEnum


class EventKind(StrEnum):
    REMOTE = "remote"
    VACATION = "vacation"
    DAY_OFF = "day_off"
    SICK = "sick"
    MEETING = "meeting"


STATUS_KINDS = frozenset(
    {
        EventKind.REMOTE,
        EventKind.VACATION,
        EventKind.DAY_OFF,
        EventKind.SICK,
    }
)

EVENT_EMOJI: dict[EventKind, str] = {
    EventKind.REMOTE: "🏠",
    EventKind.VACATION: "🌴",
    EventKind.DAY_OFF: "🛑",
    EventKind.SICK: "🤒",
    EventKind.MEETING: "🤝",
}

EVENT_LABELS: dict[EventKind, str] = {
    EventKind.REMOTE: "удаленно",
    EventKind.VACATION: "отпуск",
    EventKind.DAY_OFF: "отгул",
    EventKind.SICK: "больничный",
    EventKind.MEETING: "встреча",
}
