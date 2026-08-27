from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import (
    CHECK_FINE_TEXT,
    HELP_TEXT,
    consent_keyboard,
    main_menu_keyboard,
)
from app.bot.states import DocumentUpload
from app.services.consent_service import PERSONAL_DATA_CONSENT_TEXT, ConsentService
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
    user = await UserService(session).get_by_telegram_id(telegram_user.id)
    if user is None:
        return

    if await ConsentService(session).has_current_consent(user.id):
        await state.set_state(DocumentUpload.waiting_for_file)
        await message.answer(
            "С возвращением!\n\n"
            "Отправьте постановление о штрафе PDF-файлом или изображением.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(DocumentUpload.waiting_for_consent)
    await message.answer(
        PERSONAL_DATA_CONSENT_TEXT,
        reply_markup=consent_keyboard(),
    )


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        f"Нажмите «{CHECK_FINE_TEXT}» и отправьте постановление о штрафе PDF или изображением.\n\n"
        "После загрузки будет создано дело, а документ сохранится для просмотра в админке."
    )
