from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core import settings


class DBHelper:
    def __init__(
        self,
        *,
        url: str | URL,
        echo: bool = False,
    ) -> None:
        self._engine: AsyncEngine = create_async_engine(
            url,
            echo=echo,
        )

        self._async_session_maker: async_sessionmaker[AsyncSession] = (
            async_sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self._engine.dispose()


db_helper = DBHelper(
    url=settings.db.postgres.dsn,
    echo=settings.db.echo,
)
