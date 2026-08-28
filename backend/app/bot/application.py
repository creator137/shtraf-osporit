from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import cases, documents, legal, start
from app.bot.middleware import DatabaseSessionMiddleware
from app.config import Settings
from app.db.session import async_session_factory


def create_bot(settings: Settings) -> Bot:
    if settings.bot_token is None:
        raise RuntimeError("BOT_TOKEN is not configured")
    return Bot(
        token=settings.bot_token.get_secret_value(),
        session=AiohttpSession(proxy=settings.telegram_proxy),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(DatabaseSessionMiddleware(async_session_factory))
    dispatcher.include_routers(start.router, cases.router, documents.router, legal.router)
    return dispatcher
