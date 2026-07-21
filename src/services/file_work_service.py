import json
import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from core.config import DATA_DIR
from core.exceptions import (
    FileNotFoundOrExpiredError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from infrastructure.redis_c.client import RedisClient

logger = logging.getLogger(__name__)

FILE_TTL_SECONDS = 60 * 60  # 1 час
CHUNK_SIZE = 1024 * 1024  # 1 MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "text/plain",
    "text/csv",
}


class FileWorkService:
    def __init__(self, redis: RedisClient):
        self._redis = redis

    async def save_upload_file_and_save_metadata(self, file: UploadFile) -> str:
        file_id = str(uuid.uuid4())
        file_path = DATA_DIR / file_id

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedFileTypeError(f"File type {file.content_type} not allowed")

        if file.size is not None and file.size > MAX_FILE_SIZE:
            raise FileTooLargeError(f"File exceeds max size of {MAX_FILE_SIZE} bytes")

        await self._save_file(file, file_path)

        metadata = {
            "file_id": file_id,
            "file_name": file.filename or "unnamed",
            "content_type": file.content_type,
            "size": file.size,
        }

        await self._redis.client.set(
            f"upload:{file_id}",
            json.dumps(metadata),
            ex=FILE_TTL_SECONDS,
        )

        return file_id

    async def _save_file(self, file: UploadFile, file_path: Path) -> None:
        async with aiofiles.open(file_path, mode="wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                await buffer.write(chunk)

    async def get_file(self, file_id: str) -> tuple[bytes, dict]:
        raw_data = await self._redis.client.get(f"upload:{file_id}")
        if raw_data is None:
            raise FileNotFoundOrExpiredError(
                f"File metadata not found or expired: {file_id}"
            )

        metadata = json.loads(raw_data)
        file_path = DATA_DIR / file_id

        if not file_path.exists():
            raise FileNotFoundOrExpiredError(f"File missing on disk: {file_id}")

        async with aiofiles.open(file_path, mode="rb") as f:
            content = await f.read()

        return content, metadata

    async def delete_file(self, file_id: str):
        file_path = DATA_DIR / file_id
        file_path.unlink(missing_ok=True)
        await self._redis.client.delete(f"upload:{file_id}")
