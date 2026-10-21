from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, UploadFile

from dependencies import (
    get_file_work_service,
    get_notification_batch_service,
    get_notification_dispatcher_service,
)
from schemas.notify_schema import (
    BatchCreatedResponseSchema,
    BatchNotificationRequestSchema,
    BatchStatusResponseSchema,
    NotificationRequestSchema,
)
from services.file_work_service import FileWorkService
from services.notification_batch_service import NotificationBatchService
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


@router.post("/batch", status_code=201)
async def create_batch(
    notify_batch_data: BatchNotificationRequestSchema,
    batch_service: Annotated[
        NotificationBatchService, Depends(get_notification_batch_service)
    ],
    idempotency_key: Annotated[str | None, Header()] = None,
) -> BatchCreatedResponseSchema:
    return await batch_service.create_batch(
        batch_data=notify_batch_data,
        idempotency_key=idempotency_key,
    )


@router.get("/batch/{batch_id}", status_code=200)
async def get_batch_status(
    batch_id: UUID,
    batch_service: Annotated[
        NotificationBatchService, Depends(get_notification_batch_service)
    ],
) -> BatchStatusResponseSchema:
    return await batch_service.get_status(batch_id=batch_id)


@router.post("/batch/{batch_id}/cancel", status_code=200)
async def cancel_batch(
    batch_id: UUID,
    batch_service: Annotated[
        NotificationBatchService, Depends(get_notification_batch_service)
    ],
):
    return await batch_service.cancel_batch(batch_id=batch_id)
