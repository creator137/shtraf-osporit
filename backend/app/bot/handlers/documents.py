from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import (
    CONSENT_ACCEPT_TEXT,
    CONSENT_DECLINE_TEXT,
    consent_keyboard,
    main_menu_keyboard,
)
from app.bot.states import DocumentUpload, LegalQuestionnaire
from app.bot.handlers.legal import begin_legal_assessment_for_case_message
from app.config import get_settings
from app.services.consent_service import ConsentService
from app.services.case_service import CaseService
from app.services.document_service import (
    BACKEND_ROOT,
    DocumentService,
    build_storage_path,
    is_supported_document,
)
from app.services.ocr_service import create_ocr_provider
from app.services.recognition_service import RecognitionService, RecognitionStatus
from app.services.user_service import UserService
from app.bot.utils import safe_answer


router = Router(name="documents")
SUPPORTED_TYPES_MESSAGE = "Поддерживаются файлы PDF, JPG, JPEG и PNG."


async def _save_document(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    telegram_file_id: str,
    original_filename: str | None,
    mime_type: str | None,
    case_id: int | None = None,
) -> None:
    if message.from_user is None:
        return
    user = await UserService(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await safe_answer(message, "Начните заново с команды /start.")
        return

    if not await ConsentService(session).has_current_consent(user.id):
        await state.set_state(DocumentUpload.waiting_for_consent)
        await safe_answer(
            message,
            "Перед загрузкой постановления нужно принять согласие.",
            reply_markup=consent_keyboard(),
        )
        return

    settings = get_settings()
    case = (
        await CaseService(session).get_for_user(user.id, case_id)
        if case_id is not None
        else await CaseService(session).create(user.id)
    )
    if case is None:
        await state.clear()
        await safe_answer(message, "Дело не найдено.", reply_markup=main_menu_keyboard())
        return
    destination: Path | None = None
    local_path: str | None = None
    recognition = None
    try:
        if settings.document_storage == "local":
            destination = build_storage_path(case.id, original_filename, mime_type)
            destination.parent.mkdir(parents=True, exist_ok=True)
            await message.bot.download(telegram_file_id, destination=destination)
            local_path = destination.relative_to(BACKEND_ROOT).as_posix()
        document = await DocumentService(session).create(
            case=case,
            telegram_file_id=telegram_file_id,
            original_filename=original_filename,
            mime_type=mime_type,
            local_path=local_path,
            update_case_status=case_id is None,
        )
        if case_id is None:
            recognition = await RecognitionService(session).create_pending_for_document(
                case, document
            )
        if case_id is None and settings.ocr_provider != "none":
            content = (
                destination.read_bytes()
                if destination is not None
                else await message.bot.download(telegram_file_id)
            )
            if content is not None:
                raw_content = content.read() if hasattr(content, "read") else content
                recognition = await RecognitionService(session).process_document(
                    case.id,
                    document,
                    raw_content,
                    create_ocr_provider(settings),
                )
    except Exception:
        if destination is not None:
            destination.unlink(missing_ok=True)
        raise

    await state.clear()
    if case_id is not None:
        await safe_answer(
            message,
            f"Материалы добавлены в дело №{case.id}.",
            reply_markup=main_menu_keyboard(),
        )
        return

    processing_message = "Документ сохранён и ожидает обработки оператором."
    if recognition is not None and recognition.status == RecognitionStatus.RECOGNIZED:
        processing_message = (
            "Данные извлечены автоматически. Оператор проверит карточку постановления."
        )
    elif recognition is not None and recognition.status == RecognitionStatus.FAILED:
        processing_message = (
            "Документ сохранён, но автоматическое распознавание не удалось. "
            "Оператор сможет заполнить карточку вручную."
        )

    await safe_answer(
        message,
        "Постановление загружено.\n\n"
        f"Дело №{case.id} создано.\n"
        f"{processing_message}",
    )
    loaded_case = await CaseService(session).get_for_user(user.id, case.id)
    if loaded_case is None:
        await safe_answer(
            message,
            "Дело создано, но анкету не удалось запустить автоматически. "
            "Откройте дело через «Мои дела».",
        )
        return
    await begin_legal_assessment_for_case_message(message, loaded_case, state, session)


async def _handle_uploaded_notice(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    telegram_file_id: str,
    original_filename: str | None,
    mime_type: str | None,
) -> None:
    current_state = await state.get_state()
    if current_state == LegalQuestionnaire.waiting_for_answer.state:
        await safe_answer(
            message,
            "Сначала ответьте на текущий вопрос анкеты.\n\n"
            "После этого можно будет загрузить новое постановление."
        )
        return
    data = await state.get_data()
    case_id = data.get("additional_case_id") if isinstance(data, dict) else None

    await _save_document(
        message=message,
        state=state,
        session=session,
        telegram_file_id=telegram_file_id,
        original_filename=original_filename,
        mime_type=mime_type,
        case_id=case_id if isinstance(case_id, int) else None,
    )


@router.message(DocumentUpload.waiting_for_consent, F.text == CONSENT_ACCEPT_TEXT)
async def accept_consent(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if message.from_user is None:
        return
    telegram_user = message.from_user
    user = await UserService(session).get_or_create(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )

    await ConsentService(session).accept_current(user)
    await state.set_data({})
    await state.set_state(DocumentUpload.waiting_for_file)
    await safe_answer(
        message,
        "Согласие сохранено. Теперь отправьте постановление о штрафе в формате PDF или изображения.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(DocumentUpload.waiting_for_consent, F.text == CONSENT_DECLINE_TEXT)
async def decline_consent(message: Message, state: FSMContext) -> None:
    await state.clear()
    await safe_answer(
        message,
        "Без согласия загрузить постановление и создать дело нельзя.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(DocumentUpload.waiting_for_consent)
async def unsupported_consent_answer(message: Message) -> None:
    await safe_answer(message, "Выберите «Согласен» или «Не согласен» на клавиатуре.")


@router.message(F.document)
async def receive_document(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    document = message.document
    if document is None:
        return
    if not is_supported_document(document.file_name, document.mime_type):
        await safe_answer(message, SUPPORTED_TYPES_MESSAGE)
        return
    await _handle_uploaded_notice(
        message=message,
        state=state,
        session=session,
        telegram_file_id=document.file_id,
        original_filename=document.file_name,
        mime_type=document.mime_type,
    )


@router.message(F.photo)
async def receive_photo(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    photo = message.photo[-1]
    await _handle_uploaded_notice(
        message=message,
        state=state,
        session=session,
        telegram_file_id=photo.file_id,
        original_filename=f"photo_{photo.file_unique_id}.jpg",
        mime_type="image/jpeg",
    )


@router.message(DocumentUpload.waiting_for_file)
async def unsupported_file(message: Message) -> None:
    await safe_answer(message, SUPPORTED_TYPES_MESSAGE)
