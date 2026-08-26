from functools import lru_cache

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request

from app.bot.application import create_bot, create_dispatcher
from app.config import get_settings


router = APIRouter(tags=["telegram"])


@lru_cache
def get_bot() -> Bot:
    return create_bot(get_settings())


@lru_cache
def get_dispatcher() -> Dispatcher:
    return create_dispatcher(get_settings())


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    if settings.telegram_webhook_secret is not None:
        if (
            x_telegram_bot_api_secret_token
            != settings.telegram_webhook_secret.get_secret_value()
        ):
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    bot = get_bot()
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await get_dispatcher().feed_update(bot, update)
    return {"ok": True}
