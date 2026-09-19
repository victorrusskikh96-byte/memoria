from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from memoria.api.routes.health import router as health_router
from memoria.core.config import get_settings
from memoria.infrastructure.database.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    return application


app = create_app()
