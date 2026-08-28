from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import CHECK_FINE_TEXT, MY_CASES_TEXT, consent_keyboard
from app.bot.states import DocumentUpload
from app.bot.handlers.legal import legal_start_button
from app.db.models import Case, CaseStatus
from app.db.models.recognition import RecognitionStatus
from app.services.case_service import CaseService
from app.services.consent_service import ConsentService, PERSONAL_DATA_CONSENT_TEXT
from app.services.user_service import UserService


router = Router(name="cases")
STATUS_LABELS = {
    CaseStatus.DOCUMENT_UPLOADED: "Документ загружен",
    CaseStatus.IN_PROGRESS: "Документ в работе",
    CaseStatus.READY: "Готов",
}
RECOGNITION_LABELS = {
    RecognitionStatus.PENDING: "Ожидает обработки",
    RecognitionStatus.PROCESSING: "Распознаётся",
    RecognitionStatus.RECOGNIZED: "Распознано",
    RecognitionStatus.FAILED: "Требуется ручная проверка",
    RecognitionStatus.VERIFIED: "Проверено оператором",
}


async def _current_user(message: Message, session: AsyncSession):
    if message.from_user is None:
        return None
    return await UserService(session).get_by_telegram_id(message.from_user.id)


def _case_list_text(cases: list[Case]) -> str:
    lines = ["Ваши дела:"]
    for case in cases:
        lines.extend(
            [
                "",
                f"Дело №{case.id}",
                f"Статус: {STATUS_LABELS[case.status]}",
                f"Дата: {case.created_at:%d.%m.%Y}",
            ]
        )
    return "\n".join(lines)


def _case_list_keyboard(cases: list[Case]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Дело №{case.id}", callback_data=f"case:{case.id}")]
            for case in cases
        ]
    )


def _case_detail_text(case: Case) -> str:
    lines = [
        f"Дело №{case.id}",
        "",
        f"Статус: {STATUS_LABELS[case.status]}",
        f"Создано: {case.created_at:%d.%m.%Y %H:%M}",
        f"Документов: {len(case.documents)}",
    ]
    for document in case.documents:
        lines.append(f"Документ: {document.original_filename or 'Без имени'}")

    recognitions = [
        document.recognition
        for document in case.documents
        if document.recognition is not None
    ]
    if recognitions:
        recognition = max(recognitions, key=lambda item: item.created_at)
        lines.append(f"Распознавание: {RECOGNITION_LABELS[recognition.status]}")

    notice = case.fine_notice
    if notice is not None:
        fields = [
            ("Номер постановления", notice.notice_number),
            ("Дата постановления", notice.notice_date),
            ("УИН", notice.uin),
            (
                "Сумма штрафа",
                f"{notice.fine_amount:,} руб.".replace(",", " ")
                if notice.fine_amount is not None
                else None,
            ),
            ("Статья", notice.article),
            ("Госномер", notice.vehicle_plate),
            ("Дата нарушения", notice.violation_datetime),
            ("Место нарушения", notice.violation_place),
            ("Орган", notice.issuing_authority),
        ]
        visible_fields = [(label, value) for label, value in fields if value]
        if visible_fields:
            lines.extend(["", "Данные постановления:"])
            lines.extend(f"{label}: {value}" for label, value in visible_fields)
        else:
            lines.extend(["", "Данные постановления пока уточняются."])
    return "\n".join(lines)


@router.message(F.text == CHECK_FINE_TEXT)
async def create_case(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    user = await _current_user(message, session)
    if user is None:
        await message.answer("Сначала отправьте команду /start.")
        return

    if not await ConsentService(session).has_current_consent(user.id):
        await state.set_state(DocumentUpload.waiting_for_consent)
        await message.answer(PERSONAL_DATA_CONSENT_TEXT, reply_markup=consent_keyboard())
        return

    await state.set_state(DocumentUpload.waiting_for_file)
    await message.answer("Отправьте постановление о штрафе в формате PDF или изображения.")


@router.message(F.text == MY_CASES_TEXT)
async def list_cases(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user is None:
        await message.answer("Сначала отправьте команду /start.")
        return

    cases = await CaseService(session).list_for_user(user.id)
    if not cases:
        await message.answer("У вас пока нет дел.")
        return

    await message.answer(
        _case_list_text(cases), reply_markup=_case_list_keyboard(cases)
    )


@router.callback_query(F.data == "cases:list")
async def list_cases_callback(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    if user is None or callback.message is None:
        return

    cases = await CaseService(session).list_for_user(user.id)
    if not cases:
        await callback.message.answer("У вас пока нет дел.")
        return
    await callback.message.answer(
        _case_list_text(cases), reply_markup=_case_list_keyboard(cases)
    )


@router.callback_query(F.data.startswith("case:"))
async def show_case(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    if callback.data is None or callback.message is None:
        return

    try:
        case_id = int(callback.data.partition(":")[2])
    except ValueError:
        return

    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        return
    case = await CaseService(session).get_for_user(user.id, case_id)
    if case is None:
        await callback.message.answer("Дело не найдено.")
        return

    completed = bool(
        case.legal_assessment
        and case.legal_assessment.status.value == "COMPLETED"
    )
    await callback.message.answer(
        _case_detail_text(case),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[legal_start_button(case.id, completed=completed)]]
        ),
    )
