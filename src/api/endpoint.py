from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, UploadFile

from dependencies import get_file_work_service, get_notification_dispatcher_service
from schemas.notify_schema import NotificationRequestSchema
from services.file_work_service import FileWorkService
from services.notification_dispatcher_service import NotificationDispatcherService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "",
    status_code=202,
    responses={
        202: {"description": "Success"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)
async def notify(
    data: NotificationRequestSchema,
    notify_service: Annotated[
        NotificationDispatcherService, Depends(get_notification_dispatcher_service)
    ],
    idempotency_key: Annotated[str | None, Header()] = None,
) -> None:
    await notify_service.notification(
        request_data=data, idempotency_key=idempotency_key
    )


@router.post(
    "/file/upload",
    status_code=202,
    responses={
        202: {"description": "Success"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)
async def notify_upload_file(
    file: Annotated[UploadFile, File()],
    service: Annotated["FileWorkService", Depends(get_file_work_service)],
) -> dict:
    """MAX_FILE_SIZE =  10 MB
    ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "application/pdf",
    "text/plain", "text/csv"}
    """
    file_id = await service.save_upload_file_and_save_metadata(
        file=file,
    )

    return {"file_id": file_id}
