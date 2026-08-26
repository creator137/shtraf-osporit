from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import (
    ENTER_NAME_TEXT,
    HELP_TEXT,
    main_menu_keyboard,
    profile_name_keyboard,
)
from app.bot.states import ProfileSetup
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
    await state.set_state(ProfileSetup.waiting_for_name)
    profile_name = " ".join(
        part for part in (telegram_user.first_name, telegram_user.last_name) if part
    )
    await message.answer(
        "Как вас указать в деле? Выберите имя из Telegram или введите ФИО вручную.",
        reply_markup=profile_name_keyboard(profile_name or None),
    )


@router.message(ProfileSetup.waiting_for_name, F.text == ENTER_NAME_TEXT)
async def request_name(message: Message) -> None:
    await message.answer("Введите ФИО одним сообщением, например: Иванов Иван Иванович.")


@router.message(ProfileSetup.waiting_for_name, F.text.startswith("✅ Использовать: "))
async def use_profile_name(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if message.from_user is None or message.text is None:
        return
    profile_name = message.text.removeprefix("✅ Использовать: ").strip()
    parts = profile_name.split(maxsplit=1)
    if not parts:
        await message.answer("Не удалось определить имя. Введите ФИО вручную.")
        return
    user = await UserService(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте команду /start.")
        return
    await UserService(session).update_name(
        user, parts[0], parts[1] if len(parts) > 1 else None
    )
    await state.clear()
    await message.answer("Имя сохранено.", reply_markup=main_menu_keyboard())


@router.message(ProfileSetup.waiting_for_name, F.text)
async def save_manual_name(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if message.from_user is None or message.text is None:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Введите минимум имя и фамилию, например: Иванов Иван.")
        return
    user = await UserService(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте команду /start.")
        return
    await UserService(session).update_name(user, parts[0], " ".join(parts[1:]))
    await state.clear()
    await message.answer("ФИО сохранено.", reply_markup=main_menu_keyboard())


@router.message(F.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        "Бот помогает подготовить данные для анализа постановления о штрафе.\n\n"
        "Сейчас доступна загрузка постановления и хранение дела."
    )
