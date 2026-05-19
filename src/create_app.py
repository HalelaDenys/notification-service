import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import main_router
from core import settings
from infrastructure import broker

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.info("Starting lifespan")
    await broker.start()

    yield

    await broker.stop()
    logging.info("Ending lifespan")


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
    )

    app.include_router(main_router)

    return app
