from core.retry_policy import RetryPolicy
from infrastructure.smtp.client import create_smtp_client
from services.stmp_notiy_service import STMPNotifyService


def create_stmp_notify_service() -> STMPNotifyService:
    return STMPNotifyService(
        smtp_client=create_smtp_client(), retry_policy=RetryPolicy()
    )
