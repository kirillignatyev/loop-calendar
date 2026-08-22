from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from loop_calendar.domain.enums import STATUS_KINDS

from .models import EventModel, UserModel


class CalendarRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: str) -> UserModel | None:
        return self.session.get(UserModel, user_id)

    def get_or_create_user(
        self,
        *,
        user_id: str,
        username: str,
    ) -> UserModel:
        user = self.get_user(user_id)

        if user is None:
            user = UserModel(
                id=user_id,
                username=username,
            )
            self.session.add(user)
            self.session.flush()
            return user

        if user.username != username:
            user.username = username
            self.session.flush()

        return user

    def list_users(self) -> list[UserModel]:
        statement = select(UserModel).order_by(UserModel.username)
        return list(self.session.scalars(statement))

    def add_event(self, event: EventModel) -> EventModel:
        self.session.add(event)
        self.session.flush()
        return event

    def get_event(self, event_id: int) -> EventModel | None:
        statement = (
            select(EventModel)
            .options(joinedload(EventModel.user))
            .where(EventModel.id == event_id)
        )
        return self.session.scalar(statement)

    def delete_event(self, event_id: int) -> None:
        self.session.execute(delete(EventModel).where(EventModel.id == event_id))
        self.session.flush()

    def find_events(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[EventModel]:
        statement = (
            select(EventModel)
            .options(joinedload(EventModel.user))
            .where(
                EventModel.start_date <= end_date,
                EventModel.end_date >= start_date,
            )
            .order_by(EventModel.start_date, EventModel.start_time, EventModel.id)
        )
        return list(self.session.scalars(statement))

    def find_user_events(
        self,
        *,
        user_id: str,
        from_date: date | None = None,
    ) -> list[EventModel]:
        statement = (
            select(EventModel)
            .options(joinedload(EventModel.user))
            .where(EventModel.user_id == user_id)
        )

        if from_date is not None:
            statement = statement.where(EventModel.end_date >= from_date)

        statement = statement.order_by(
            EventModel.start_date,
            EventModel.start_time,
            EventModel.id,
        )
        return list(self.session.scalars(statement))

    def find_status_conflicts(
        self,
        *,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> list[EventModel]:
        statement = (
            select(EventModel)
            .where(
                EventModel.user_id == user_id,
                EventModel.kind.in_(tuple(STATUS_KINDS)),
                EventModel.start_date <= end_date,
                EventModel.end_date >= start_date,
            )
            .order_by(EventModel.start_date, EventModel.id)
        )
        return list(self.session.scalars(statement))

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
