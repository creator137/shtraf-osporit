from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import (
    CHECK_FINE_TEXT,
    HELP_TEXT,
    main_menu_keyboard,
)
from app.services.user_service import UserService


router = Router(name="start")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return

    await UserService(session).get_or_create(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )
    await state.clear()
    await message.answer(
        "Добро пожаловать в сервис «Штраф.Оспорить»!\n\n"
        "Чтобы начать, нажмите «Оспорить штраф», подтвердите согласие "
        "на обработку данных и отправьте постановление о штрафе "
        "PDF-файлом или изображением.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        f"Нажмите «{CHECK_FINE_TEXT}» и отправьте постановление о штрафе PDF или изображением.\n\n"
        "После загрузки будет создано дело, а документ сохранится для просмотра в админке."
    )
