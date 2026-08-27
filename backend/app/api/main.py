from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.telegram import router as telegram_router
from app.config import get_settings


settings = get_settings()
app = FastAPI(title="Shtraf.Osporit API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.admin_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(telegram_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
