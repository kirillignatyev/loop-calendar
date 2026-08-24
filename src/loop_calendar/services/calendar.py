from datetime import date

from loop_calendar.db.models import EventModel, UserModel
from loop_calendar.db.repository import CalendarRepository
from loop_calendar.domain.commands import AddMeeting, AddStatus
from loop_calendar.domain.enums import EVENT_LABELS, EventKind
from loop_calendar.domain.errors import EventConflict, EventNotFound, PermissionDenied


class CalendarService:
    def __init__(self, repository: CalendarRepository) -> None:
        self.repository = repository

    def ensure_user(
        self,
        *,
        user_id: str,
        username: str,
    ) -> UserModel:
        user = self.repository.get_or_create_user(
            user_id=user_id,
            username=username,
        )
        self.repository.commit()
        return user

    def add_status(
        self,
        *,
        user_id: str,
        username: str,
        command: AddStatus,
    ) -> EventModel:
        self.repository.get_or_create_user(
            user_id=user_id,
            username=username,
        )

        conflicts = self.repository.find_status_conflicts(
            user_id=user_id,
            start_date=command.start_date,
            end_date=command.end_date,
        )
        if conflicts:
            conflict = conflicts[0]
            label = EVENT_LABELS[conflict.kind]
            raise EventConflict(
                "У вас уже есть пересекающийся статус "
                f"`#{conflict.id}`: **{label}**, "
                f"{conflict.start_date:%d.%m.%Y}–"
                f"{conflict.end_date:%d.%m.%Y}. "
                f"Сначала удалите его: `/cal delete {conflict.id}`."
            )
        event = EventModel(
            user_id=user_id,
            kind=command.kind,
            start_date=command.start_date,
            end_date=command.end_date,
        )
        self.repository.add_event(event)
        self.repository.commit()
        return event

    def add_meeting(
        self,
        *,
        user_id: str,
        username: str,
        command: AddMeeting,
    ) -> EventModel:
        self.repository.get_or_create_user(
            user_id=user_id,
            username=username,
        )

        event = EventModel(
            user_id=user_id,
            kind=EventKind.MEETING,
            start_date=command.date,
            end_date=command.date,
            start_time=command.start_time,
            end_time=command.end_time,
            title=command.title,
        )
        self.repository.add_event(event)
        self.repository.commit()
        return event

    def delete_event(
        self,
        *,
        event_id: int,
        user_id: str,
    ) -> EventModel:
        event = self.repository.get_event(event_id)

        if event is None:
            raise EventNotFound(f"Событие `#{event_id}` не найдено.")

        if event.user_id != user_id:
            raise PermissionDenied("Можно удалять только собственные события.")

        self.repository.delete_event(event_id)
        self.repository.commit()
        return event

    def events_between(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[EventModel]:
        return self.repository.find_events(
            start_date=start_date,
            end_date=end_date,
        )

    def my_events(
        self,
        *,
        user_id: str,
        from_date: date,
    ) -> list[EventModel]:
        return self.repository.find_user_events(
            user_id=user_id,
            from_date=from_date,
        )
