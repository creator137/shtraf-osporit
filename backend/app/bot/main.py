import asyncio
import logging

from app.bot.application import create_bot, create_dispatcher
from app.config import get_settings
from app.db.session import engine


async def main() -> None:
    settings = get_settings()
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        )
    finally:
        await dispatcher.storage.close()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
