from aiogram.exceptions import TelegramAPIError


async def safe_answer(message, text: str, **kwargs):
    try:
        return await message.answer(text, **kwargs)
    except TelegramAPIError:
        return None


async def safe_callback_answer(callback, text: str | None = None, **kwargs):
    try:
        return await callback.answer(text, **kwargs)
    except TelegramAPIError:
        return None
