from fastapi import APIRouter

main_router = APIRouter(
    prefix="/api/v1",
)


@main_router.get("")
async def health() -> dict:
    return {"status": "ok"}
