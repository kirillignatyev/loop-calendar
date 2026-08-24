from contextlib import asynccontextmanager

from fastapi import FastAPI

from loop_calendar.api.loop import router
from loop_calendar.db.database import get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app

    database = get_database()
    database.init()

    yield


app = FastAPI(
    title="Loop Calendar",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
