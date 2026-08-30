from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import (
    CHECK_FINE_TEXT,
    HELP_TEXT,
    consent_keyboard,
    main_menu_keyboard,
)
from app.bot.utils import safe_answer
from app.bot.states import DocumentUpload
from app.services.consent_service import PERSONAL_DATA_CONSENT_TEXT, ConsentService
from app.services.user_service import UserService


router = Router(name="start")


@router.message(Command("restart"))
async def restart(message: Message, state: FSMContext, session: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return

    deleted = await UserService(session).delete_by_telegram_id(telegram_user.id)
    await state.clear()
    if deleted:
        await safe_answer(
            message,
            "Ваш профиль, согласия и дела удалены.\n\n"
            "Чтобы начать заново, отправьте команду /start."
        )
        return

    await safe_answer(
        message,
        "Профиль и дела не найдены.\n\n"
        "Чтобы начать, отправьте команду /start."
    )


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return

    await state.clear()
    user = await UserService(session).get_by_telegram_id(telegram_user.id)
    if user is not None and await ConsentService(session).has_current_consent(user.id):
        await UserService(session).get_or_create(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )
        await state.set_state(DocumentUpload.waiting_for_file)
        await safe_answer(
            message,
            "С возвращением!\n\n"
            "Отправьте постановление о штрафе PDF-файлом или изображением.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(DocumentUpload.waiting_for_consent)
    await safe_answer(
        message,
        PERSONAL_DATA_CONSENT_TEXT,
        reply_markup=consent_keyboard(),
    )


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await safe_answer(
        message,
        f"Нажмите «{CHECK_FINE_TEXT}» и отправьте постановление о штрафе PDF или изображением.\n\n"
        "После загрузки будет создано дело, а документ сохранится для просмотра в админке."
    )
