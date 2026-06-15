from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies import get_notify_service
from schemas.notify_schema import NotificationRequestSchema
from services.broker_notify_service import BrokerNotifyService

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
    notify_service: Annotated[BrokerNotifyService, Depends(get_notify_service)],
) -> None:
    await notify_service.send(data=data)
