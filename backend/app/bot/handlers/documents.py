from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import MY_CASES_TEXT
from app.bot.states import DocumentUpload
from app.config import get_settings
from app.services.case_service import CaseService
from app.services.document_service import (
    BACKEND_ROOT,
    DocumentService,
    build_storage_path,
    is_supported_document,
)
from app.services.user_service import UserService


router = Router(name="documents")
SUPPORTED_TYPES_MESSAGE = "Поддерживаются файлы PDF, JPG, JPEG и PNG."


async def _save_document(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    telegram_file_id: str,
    original_filename: str | None,
    mime_type: str | None,
) -> None:
    if message.from_user is None:
        return
    user = await UserService(session).get_by_telegram_id(message.from_user.id)
    state_data = await state.get_data()
    case_id = state_data.get("case_id")
    if user is None or not isinstance(case_id, int):
        await state.clear()
        await message.answer("Начните заново с команды /start.")
        return

    case = await CaseService(session).get_for_user(user.id, case_id)
    if case is None:
        await state.clear()
        await message.answer("Дело не найдено. Начните заново с команды /start.")
        return

    settings = get_settings()
    destination: Path | None = None
    local_path: str | None = None
    try:
        if settings.document_storage == "local":
            destination = build_storage_path(case.id, original_filename, mime_type)
            destination.parent.mkdir(parents=True, exist_ok=True)
            await message.bot.download(telegram_file_id, destination=destination)
            local_path = destination.relative_to(BACKEND_ROOT).as_posix()
        await DocumentService(session).create(
            case=case,
            telegram_file_id=telegram_file_id,
            original_filename=original_filename,
            mime_type=mime_type,
            local_path=local_path,
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    await state.clear()
    await message.answer(
        "Постановление загружено.\n\n"
        f"Дело №{case.id} создано.\n"
        "На следующем этапе система сможет распознать данные постановления.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=MY_CASES_TEXT, callback_data="cases:list")]
            ]
        ),
    )


@router.message(DocumentUpload.waiting_for_file, F.document)
async def receive_document(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    document = message.document
    if document is None:
        return
    if not is_supported_document(document.file_name, document.mime_type):
        await message.answer(SUPPORTED_TYPES_MESSAGE)
        return
    await _save_document(
        message=message,
        state=state,
        session=session,
        telegram_file_id=document.file_id,
        original_filename=document.file_name,
        mime_type=document.mime_type,
    )


@router.message(DocumentUpload.waiting_for_file, F.photo)
async def receive_photo(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    photo = message.photo[-1]
    await _save_document(
        message=message,
        state=state,
        session=session,
        telegram_file_id=photo.file_id,
        original_filename=f"photo_{photo.file_unique_id}.jpg",
        mime_type="image/jpeg",
    )


@router.message(DocumentUpload.waiting_for_file)
async def unsupported_file(message: Message) -> None:
    await message.answer(SUPPORTED_TYPES_MESSAGE)
