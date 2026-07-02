from fastapi import APIRouter

from api.endpoint import router

main_router = APIRouter(
    prefix="/api/v1",
)

main_router.include_router(router)
