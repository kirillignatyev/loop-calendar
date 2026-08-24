from collections.abc import Generator
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from loop_calendar.api import loop as loop_api
from loop_calendar.config import Settings, get_settings
from loop_calendar.db.database import Database, get_session

TOKEN = "test-token"
TODAY = date(2026, 8, 24)


@pytest.fixture
def api_database() -> Database:
    database = Database("sqlite:///:memory:")
    database.init()
    return database


@pytest.fixture
def client(
    api_database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient]:
    app = FastAPI()
    app.include_router(loop_api.router)

    settings = Settings(
        loop_slash_token=TOKEN,
        database_url="sqlite:///:memory:",
        timezone="Europe/Riga",
    )

    def override_session() -> Generator[Session]:
        with api_database.session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(loop_api, "local_today", lambda _timezone: TODAY)

    with TestClient(app) as test_client:
        yield test_client


def post_command(
    client: TestClient,
    text: str,
    *,
    token: str = TOKEN,
    authorization: str | None = f"Token {TOKEN}",
    user_id: str = "u1",
    user_name: str = "kirill",
):
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization

    return client.post(
        "/loop/command",
        data={
            "text": text,
            "token": token,
            "user_id": user_id,
            "user_name": user_name,
        },
        headers=headers,
    )


def test_rejects_invalid_form_token(client: TestClient) -> None:
    response = post_command(client, "today", token="wrong")

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Loop token."


def test_requires_authorization_header(client: TestClient) -> None:
    response = post_command(client, "today", authorization=None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing Authorization header."


@pytest.mark.parametrize("scheme", ["Token", "token", "Bearer", "bearer"])
def test_accepts_supported_authorization_schemes(
    client: TestClient,
    scheme: str,
) -> None:
    response = post_command(client, "help", authorization=f"{scheme} {TOKEN}")

    assert response.status_code == 200
    assert response.json()["response_type"] == "ephemeral"


def test_requires_user_identity(client: TestClient) -> None:
    response = post_command(client, "today", user_id="")

    assert response.status_code == 400
    assert "user_id/user_name" in response.json()["detail"]


def test_add_status_and_show_mine(client: TestClient) -> None:
    created = post_command(client, "remote tomorrow")

    assert created.status_code == 200
    assert "Удаленно добавлено" in created.json()["text"]
    assert "25 августа 2026" in created.json()["text"]

    mine = post_command(client, "mine")

    assert mine.status_code == 200
    assert "## Ваш календарь" in mine.json()["text"]
    assert "🏠" in mine.json()["text"]


def test_conflict_is_returned_as_ephemeral_message(client: TestClient) -> None:
    first = post_command(client, "vacation 25.08-30.08")
    second = post_command(client, "sick 30.08-31.08")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["response_type"] == "ephemeral"
    assert second.json()["text"].startswith("⚠️ ")
    assert "пересекающийся статус" in second.json()["text"]


def test_user_cannot_delete_another_users_event(client: TestClient) -> None:
    created = post_command(client, "off 28.08", user_id="u1", user_name="kirill")
    event_id = created.json()["text"].split("`#", 1)[1].split("`", 1)[0]

    response = post_command(
        client,
        f"delete {event_id}",
        user_id="u2",
        user_name="anna",
    )

    assert response.status_code == 200
    assert "⚠️ Можно удалять только собственные события." == response.json()["text"]


def test_unknown_command_is_user_facing_error(client: TestClient) -> None:
    response = post_command(client, "abracadabra")

    assert response.status_code == 200
    assert response.json()["response_type"] == "ephemeral"
    assert response.json()["text"].startswith("⚠️ ")
