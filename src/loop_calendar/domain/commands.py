from dataclasses import dataclass
from datetime import date, time
from typing import Literal

from .enums import EventKind


@dataclass(frozen=True, slots=True)
class AddStatus:
    kind: EventKind
    start_date: date
    end_date: date


@dataclass(frozen=True, slots=True)
class AddMeeting:
    date: date
    start_time: time
    end_time: time
    title: str


@dataclass(frozen=True, slots=True)
class DeleteEvent:
    event_id: int


@dataclass(frozen=True, slots=True)
class ShowCalendar:
    scope: Literal["today", "week", "mine"]


@dataclass(frozen=True, slots=True)
class ShowHelp:
    pass


CalendarCommand = AddStatus | AddMeeting | DeleteEvent | ShowCalendar | ShowHelp
