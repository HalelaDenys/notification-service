from typing import Any, Generic, TypeVar

from sqlalchemy import delete as delete_sql
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import MultipleRowsFoundError, RepositoryError
from infrastructure.db.models import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
IMMUTABLE_FIELDS = {"id", "created_at"}


class BaseSQLAlchemyRepository(Generic[ModelType]):
    """Generic SQLAlchemy repository for simple CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self._model = model
        self._session = session
        self._mapper = inspect(model)
        self._column_names = set(self._mapper.columns.keys())

    def _get_column(self, field_name: str):
        if field_name not in self._column_names:
            raise RepositoryError(
                f"Unknown field '{field_name}' for {self._model.__name__}"
            )
        return getattr(self._model, field_name)

    def _apply_filters(self, stmt, filters: dict[str, Any]):
        for key, value in filters.items():
            stmt = stmt.where(self._get_column(key) == value)
        return stmt

    def _validate_payload(
        self, payload: dict[str, Any], *, allow_immutable: bool
    ) -> None:
        for field_name in payload:
            self._get_column(field_name)
            if not allow_immutable and field_name in IMMUTABLE_FIELDS:
                raise RepositoryError(
                    f"Field '{field_name}' is immutable for {self._model.__name__}"
                )

    def _require_filters(self, filters: dict[str, Any], action: str) -> None:
        if not filters:
            raise RepositoryError(
                f"{action} on {self._model.__name__} requires at least one filter"
            )

    async def create(self, data: dict[str, Any]) -> ModelType:
        self._validate_payload(data, allow_immutable=False)
        obj = self._model(**data)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def find_one(self, **filters: Any) -> ModelType | None:
        self._require_filters(filters, "find_one")

        stmt = self._apply_filters(select(self._model), filters).limit(2)
        res = await self._session.execute(stmt)
        rows = res.scalars().all()

        if not rows:
            return None

        if len(rows) > 1:
            raise MultipleRowsFoundError(
                f"Expected one {self._model.__name__}, got {len(rows)} "
                f"for filters={filters}"
            )

        return rows[0]

    async def find_many(self, **filters: Any) -> list[ModelType]:
        stmt = self._apply_filters(select(self._model), filters)
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def update(self, data: dict[str, Any], **filters: Any) -> ModelType | None:
        self._require_filters(filters, "update")
        self._validate_payload(data, allow_immutable=False)

        obj = await self.find_one(**filters)
        if obj is None:
            return None

        for key, value in data.items():
            setattr(obj, key, value)

        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete_one(self, **filters: Any) -> bool:
        self._require_filters(filters, "delete_one")

        obj = await self.find_one(**filters)
        if obj is None:
            return False

        await self._session.delete(obj)
        await self._session.flush()
        return True

    async def delete_many(self, *, allow_all: bool = False, **filters: Any) -> int:
        if not filters and not allow_all:
            raise RepositoryError(
                f"delete_many on {self._model.__name__} "
                f"requires filters or allow_all=True"
            )

        stmt = delete_sql(self._model)
        stmt = self._apply_filters(stmt, filters)
        res = await self._session.execute(
            stmt.execution_options(synchronize_session=False)
        )
        return int(res.rowcount or 0)
