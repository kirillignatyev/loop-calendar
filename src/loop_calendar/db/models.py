from datetime import UTC, date, datetime, time

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from loop_calendar.domain.enums import EventKind

from .base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


event_kind_type = Enum(
    EventKind,
    name="event_kind",
    native_enum=False,
    validate_strings=True,
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(256))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    events: Mapped[list["EventModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[str] = mapped_column(
        event_kind_type,
        bullable=False,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped[UserModel] = relationship(back_populates="events")
