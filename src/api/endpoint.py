from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies import get_notify_service
from schemas.notify_schema import NotificationRequestSchema
from services.broker_notify_service import BrokerNotifyService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# templates = Jinja2Templates(directory="templates")


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


# @router.get(
#     "/items",
# )
# async def read_item(
#     request: Request,
# ):
#     return templates.TemplateResponse(
#         request=request,
#         name="email/notification.html",
#         context={
#             "type": "Notification",
#             "subject": "Your account was updated",
#             "message": "We've successfully updated your account settings. "
#                        "If you didn't request this change,
#                        please contact support immediately.",
#             "action_url": "https://example.com/account",
#             "action_text": "View account",
#             "recipient": "user@example.com",
#         },
#     )
