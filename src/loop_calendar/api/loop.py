import secrets
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Form, Header, HTTPException
from sqlalchemy.orm import Session

from loop_calendar.config import Settings, get_settings
from loop_calendar.db.database import get_session
from loop_calendar.db.repository import CalendarRepository
from loop_calendar.domain.commands import (
    AddMeeting,
    AddStatus,
    DeleteEvent,
    ShowCalendar,
    ShowHelp,
)
from loop_calendar.domain.errors import CalendarError
from loop_calendar.domain.parser import parse_command
from loop_calendar.services.calendar import CalendarService
from loop_calendar.services.markdown import (
    MarkdownRenderer,
    MarkdownService,
)

router = APIRouter()


@router.post("/loop/command")
def loop_command(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    text: Annotated[str, Form()] = "",
    token: Annotated[str | None, Form()] = None,
    user_id: Annotated[str, Form()] = "",
    user_name: Annotated[str, Form()] = "",
    channel_id: Annotated[str | None, Form()] = None,
    team_id: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    del channel_id, team_id

    verify_loop_request(
        form_token=token,
        authorization=authorization,
        expected_token=settings.loop_slash_token,
    )

    if not user_id or not user_name:
        raise HTTPException(
            status_code=400,
            detail="Loop request does not contain user_id/user_name.",
        )

    today = local_today(settings.timezone)

    repository = CalendarRepository(session)
    calendar_service = CalendarService(repository)

    renderer = MarkdownRenderer()
    markdown_service = MarkdownService(
        repository=repository,
        renderer=renderer,
    )

    try:
        command = parse_command(
            text,
            today=today,
        )

        calendar_service.ensure_user(
            user_id=user_id,
            username=user_name,
        )

        if isinstance(command, ShowHelp):
            response_text = markdown_service.render_help()

        elif isinstance(command, ShowCalendar):
            if command.scope == "today":
                response_text = markdown_service.render_today(
                    target_date=today,
                )

            elif command.scope == "week":
                response_text = markdown_service.render_week(
                    today=today,
                )

            elif command.scope == "mine":
                response_text = markdown_service.render_mine(
                    user_id=user_id,
                    from_date=today,
                )

            else:
                raise TypeError(f"Unsupported command type: {type(command)!r}")

        elif isinstance(command, AddStatus):
            event = calendar_service.add_status(
                user_id=user_id,
                username=user_name,
                command=command,
            )

            response_text = renderer.render_created(event)

        elif isinstance(command, AddMeeting):
            event = calendar_service.add_meeting(
                user_id=user_id,
                username=user_name,
                command=command,
            )

            response_text = renderer.render_created(event)

        elif isinstance(command, DeleteEvent):
            event = calendar_service.delete_event(
                event_id=command.event_id,
                user_id=user_id,
            )

            response_text = renderer.render_deleted(event)

        else:
            raise TypeError(f"Unsupported command type: {type(command)!r}")

    except CalendarError as exc:
        return {
            "response_type": "ephemeral",
            "text": f"⚠️ {exc}",
        }

    return {
        "response_type": "ephemeral",
        "text": response_text,
    }


def verify_loop_request(
    *,
    form_token: str | None,
    authorization: str | None,
    expected_token: str,
) -> None:
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="LOOP_SLASH_TOKEN is not configured.",
        )

    if not form_token or not secrets.compare_digest(
        form_token,
        expected_token,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid Loop token.",
        )

    if authorization is None:
        raise HTTPException(
            status_code=403,
            detail="Missing Authorization header.",
        )

    scheme, separator, header_token = authorization.partition(" ")

    if (
        not separator
        or scheme.lower() not in {"token", "bearer"}
        or not secrets.compare_digest(
            header_token,
            expected_token,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid Authorization header.",
        )


def local_today(timezone: str) -> date:
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unknown timezone: {timezone}",
        ) from exc

    return datetime.now(tz).date()
