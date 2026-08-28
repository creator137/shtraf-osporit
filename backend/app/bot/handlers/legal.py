from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LegalAssessment, LegalAssessmentStatus
from app.services.case_service import CaseService
from app.services.legal_assessment_service import LegalAssessmentService
from app.services.legal_rules import EvidenceStatus, LegalQuestion, get_next_question
from app.services.user_service import UserService


router = Router(name="legal")


def legal_start_button(case_id: int, *, completed: bool = False) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="Посмотреть результат" if completed else "Пройти юридическую анкету",
        callback_data=f"legal:start:{case_id}",
    )


def _question_keyboard(case_id: int, question: LegalQuestion) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=option.label,
                    callback_data=(
                        f"legal:answer:{case_id}:{question.id}:{option.value}"
                    ),
                )
            ]
            for option in question.options
        ]
    )


def _result_keyboard(case_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пройти заново", callback_data=f"legal:restart:{case_id}"
                )
            ],
            [InlineKeyboardButton(text="📁 Мои дела", callback_data="cases:list")],
        ]
    )


def _result_text(assessment: LegalAssessment) -> str:
    lines = [
        "Предварительная юридическая проверка завершена.",
        "",
        "Это направления для дополнительной проверки, а не готовая жалоба или гарантия отмены штрафа.",
    ]
    if not assessment.results:
        lines.extend(
            [
                "",
                "По ответам явные направления для проверки не определены.",
            ]
        )
        return "\n".join(lines)

    lines.extend(["", "Возможные направления:"])
    evidence_labels = {
        EvidenceStatus.AVAILABLE.value: "есть подтверждающие материалы",
        EvidenceStatus.NEEDED.value: "нужны подтверждающие материалы",
        EvidenceStatus.VERIFY.value: "нужно запросить и проверить сведения",
    }
    for result in assessment.results:
        evidence = evidence_labels.get(
            str(result.get("evidence_status")), "требуется проверка"
        )
        lines.extend(
            [
                "",
                f"{result['code']} · {result['title']}",
                str(result["direction"]),
                f"Доказательства: {evidence}.",
            ]
        )
    return "\n".join(lines)


async def _case_for_callback(
    callback: CallbackQuery, case_id: int, session: AsyncSession
):
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        return None
    return await CaseService(session).get_for_user(user.id, case_id)


async def _show_question(
    callback: CallbackQuery, case_id: int, question: LegalQuestion
) -> None:
    if callback.message is None:
        return
    await callback.message.answer(
        f"Юридическая анкета по делу №{case_id}\n\n{question.text}",
        reply_markup=_question_keyboard(case_id, question),
    )


@router.callback_query(F.data.startswith("legal:start:"))
async def start_assessment(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    if callback.data is None or callback.message is None:
        return
    try:
        case_id = int(callback.data.rpartition(":")[2])
    except ValueError:
        return

    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await callback.message.answer("Дело не найдено.")
        return

    service = LegalAssessmentService(session)
    assessment = await service.start(case.id)
    if assessment.status is LegalAssessmentStatus.COMPLETED:
        await callback.message.answer(
            _result_text(assessment), reply_markup=_result_keyboard(case.id)
        )
        return

    question = get_next_question(assessment.answers)
    if question is not None:
        await _show_question(callback, case.id, question)


@router.callback_query(F.data.startswith("legal:restart:"))
async def restart_assessment(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    if callback.data is None or callback.message is None:
        return
    try:
        case_id = int(callback.data.rpartition(":")[2])
    except ValueError:
        return
    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await callback.message.answer("Дело не найдено.")
        return
    assessment = await LegalAssessmentService(session).start(case.id, restart=True)

    question = get_next_question(assessment.answers)
    if question is not None:
        await _show_question(callback, case.id, question)


@router.callback_query(F.data.startswith("legal:answer:"))
async def answer_question(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 5 or parts[0:2] != ["legal", "answer"]:
        await callback.answer("Некорректный ответ", show_alert=True)
        return
    _, _, case_value, question_id, value = parts
    try:
        case_id = int(case_value)
    except ValueError:
        return

    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await callback.answer("Дело не найдено", show_alert=True)
        return
    assessment = await LegalAssessmentService(session).get_for_case(case.id)
    if assessment is None:
        await callback.answer("Начните анкету заново", show_alert=True)
        return

    try:
        next_question = await LegalAssessmentService(session).answer(
            assessment, question_id, value
        )
    except ValueError:
        await callback.answer("Этот вопрос уже обработан", show_alert=True)
        return
    await callback.answer()
    if next_question is not None:
        await _show_question(callback, case.id, next_question)
        return
    await callback.message.answer(
        _result_text(assessment), reply_markup=_result_keyboard(case.id)
    )
