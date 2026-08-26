import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import cases, documents, start
from app.bot.middleware import DatabaseSessionMiddleware
from app.config import get_settings
from app.db.session import async_session_factory, engine


async def main() -> None:
    settings = get_settings()
    if settings.bot_token is None:
        raise RuntimeError("BOT_TOKEN is not configured")

    bot = Bot(token=settings.bot_token.get_secret_value())
    dispatcher = Dispatcher()
    dispatcher.update.middleware(DatabaseSessionMiddleware(async_session_factory))
    dispatcher.include_routers(start.router, cases.router, documents.router)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        )
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
