import logging
from datetime import timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import LegalQuestionnaire
from app.bot.keyboards.main import (
    CHECK_FINE_TEXT,
    HELP_TEXT,
    MY_CASES_TEXT,
    main_menu_keyboard,
)
from app.bot.utils import safe_answer, safe_callback_answer
from app.db.models import (
    GeneratedDocumentFormat,
    LegalAnalysis,
    LegalAssessment,
    LegalAssessmentStatus,
    LegalGroundStatus,
)
from app.services.case_service import CaseService
from app.services.generated_document_service import generated_file_path
from app.services.legal_analysis_service import LegalAnalysisService
from app.services.legal_assessment_service import LegalAssessmentService
from app.services.legal_rules import (
    EvidenceStatus,
    LegalQuestion,
    answer_label,
    format_date,
    get_next_question,
    get_question,
    parse_date,
)
from app.services.user_service import UserService

router = Router(name="legal")
logger = logging.getLogger(__name__)

GROUND_STATUS_LABELS = {
    LegalGroundStatus.PROPOSED.value: "Предложено системой",
    LegalGroundStatus.CONFIRMED.value: "Подтверждено пользователем",
    LegalGroundStatus.REJECTED.value: "Отклонено пользователем",
}

SOURCE_LABELS = {
    "koap-rf": "КоАП РФ",
    "plenum-vs-20": "Постановление Пленума Верховного Суда РФ № 20",
}


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


def _latest_ocr_text(case) -> str | None:
    recognitions = [
        document.recognition
        for document in case.documents
        if document.recognition is not None and document.recognition.raw_text
    ]
    if not recognitions:
        return None
    latest = max(recognitions, key=lambda item: item.created_at)
    return latest.raw_text


def _case_context(case) -> tuple[str | None, str | None, str | None]:
    notice = case.fine_notice
    return (
        notice.article if notice else None,
        _latest_ocr_text(case),
        notice.violation_place if notice else None,
    )


async def _ask_question(
    message,
    case_id: int,
    question: LegalQuestion,
    state: FSMContext,
) -> None:
    if question.input_kind in {"date", "text"}:
        await state.set_state(LegalQuestionnaire.waiting_for_answer)
        await state.update_data(case_id=case_id, question_id=question.id)
        await safe_answer(
            message,
            f"Юридическая анкета по делу №{case_id}\n\n{question.text}",
            reply_markup=main_menu_keyboard(),
        )
        return
    await state.clear()
    await safe_answer(
        message,
        f"Юридическая анкета по делу №{case_id}\n\n{question.text}",
        reply_markup=_question_keyboard(case_id, question),
    )


def _appeal_summary(answers: dict[str, str]) -> list[str]:
    lines: list[str] = []
    received = parse_date(answers.get("appeal_received_at"))
    if received is None:
        return lines
    deadline = received + timedelta(days=10)
    deadline_text = format_date(deadline) or deadline.strftime("%d.%m.%Y")
    lines.append(f"Срок обжалования: до {deadline_text}.")
    if answers.get("appeal_delay_reason"):
        lines.append(
            f"Причина пропуска: {answer_label('appeal_delay_reason', answers.get('appeal_delay_reason') or '')}"
        )
        lines.append("Нужно ходатайство о восстановлении срока: да.")
    else:
        lines.append("Нужно ходатайство о восстановлении срока: нет.")
    return lines


def _result_keyboard(case_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Запустить анализ ИИ",
                    callback_data=f"ai:start:{case_id}",
                )
            ],
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
        "Результат предварительной проверки оснований для обжалования",
        "",
        "Система сопоставила ваши ответы с юридическими правилами и определила, что стоит проверить перед подготовкой жалобы.",
        "Это не готовая жалоба и не гарантия отмены штрафа.",
    ]
    lines.extend(_appeal_summary(assessment.answers))
    if not assessment.results:
        lines.extend(
            [
                "",
                "По ответам явные направления для проверки не определены.",
            ]
        )
        return "\n".join(lines)

    lines.extend(["", "Что стоит проверить:"])
    for index, result in enumerate(assessment.results, start=1):
        evidence_items = result.get("evidence_items", [])
        available = [
            str(item.get("name"))
            for item in evidence_items
            if item.get("status") == EvidenceStatus.AVAILABLE.value
        ]
        missing = [
            str(item.get("name"))
            for item in evidence_items
            if item.get("status") == EvidenceStatus.NEEDED.value
        ]
        verify = [
            str(item.get("name"))
            for item in evidence_items
            if item.get("status") == EvidenceStatus.VERIFY.value
        ]
        lines.extend(
            [
                "",
                f"{index}. {result['title']}",
                f"Что проверить: {result['direction']}",
                "Почему выбрано это направление: "
                + " ".join(result.get("reasons", [])),
            ]
        )
        if available:
            lines.append(f"Уже есть для подтверждения: {', '.join(available)}.")
        if missing:
            lines.append(
                "Для подтверждения понадобятся: " + ", ".join(missing) + "."
            )
        if verify:
            lines.append(
                "Следует запросить или дополнительно проверить: "
                + ", ".join(verify)
                + "."
            )
        if not available and not missing and not verify:
            lines.append("Дополнительные материалы по этому направлению не указаны.")
    lines.extend(
        [
            "",
            "Следующий шаг: запустите анализ ИИ. Он подготовит возможные доводы на основе результатов проверки, после чего вы сможете выбрать, какие из них использовать в жалобе.",
        ]
    )
    return "\n".join(lines)


def _analysis_keyboard(case_id: int, analysis: LegalAnalysis) -> InlineKeyboardMarkup:
    rows = []
    for ground in analysis.grounds:
        ground_id = str(ground.get("id"))
        title = str(ground.get("title") or ground_id)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Использовать: {title[:32]}",
                    callback_data=f"ai:ground:{case_id}:{ground_id}:confirm",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Не использовать: {title[:28]}",
                    callback_data=f"ai:ground:{case_id}:{ground_id}:reject",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Подготовить документы",
                callback_data=f"ai:docs:{case_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _analysis_text(analysis: LegalAnalysis) -> str:
    result = analysis.result or {}
    lines = [
        "Анализ ИИ завершён.",
        "",
        str(result.get("summary") or "Система предложила возможные основания."),
        "",
        str(result.get("overall_assessment") or "Оценка предварительная, без гарантии результата."),
    ]
    if not analysis.grounds:
        lines.extend(["", "Валидные основания не найдены."])
        return "\n".join(lines)

    lines.extend(["", "Предложенные основания:"])
    for index, ground in enumerate(analysis.grounds, start=1):
        rules = ", ".join(str(item) for item in ground.get("legal_rule_ids", []))
        sources = ", ".join(
            SOURCE_LABELS.get(str(item), str(item))
            for item in ground.get("source_ids", [])
        )
        status = GROUND_STATUS_LABELS.get(
            str(ground.get("status")), "Ожидает решения пользователя"
        )
        lines.extend(
            [
                "",
                f"{index}. {ground.get('title')}",
                str(ground.get("description") or ""),
                f"Юридические правила: {rules or 'не указаны'}.",
                f"Источники: {sources or 'не указаны'}.",
                "Что нужно дополнительно: "
                + (
                    ", ".join(ground.get("missing_evidence", []))
                    if ground.get("missing_evidence")
                    else "нет"
                ),
                f"Статус: {status}.",
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


async def _case_for_telegram_user(
    session: AsyncSession, telegram_id: int, case_id: int
):
    user = await UserService(session).get_by_telegram_id(telegram_id)
    if user is None:
        return None
    return await CaseService(session).get_for_user(user.id, case_id)


async def _show_question(
    message, case_id: int, question: LegalQuestion, state: FSMContext
) -> None:
    if message is None:
        return
    await _ask_question(message, case_id, question, state)


async def begin_legal_assessment_for_case_message(
    message,
    case,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    service = LegalAssessmentService(session)
    article, ocr_text, violation_place = _case_context(case)
    assessment = await service.start_with_context(
        case.id,
        violation_datetime=case.fine_notice.violation_datetime if case.fine_notice else None,
        notice_date=case.fine_notice.notice_date if case.fine_notice else None,
        complaint_recipient=(
            case.fine_notice.issuing_authority if case.fine_notice else None
        ),
    )
    if assessment.status is LegalAssessmentStatus.COMPLETED:
        await safe_answer(
            message,
            _result_text(assessment),
            reply_markup=_result_keyboard(case.id),
        )
        return

    question = get_next_question(
        assessment.answers,
        article,
        ocr_text,
        violation_place,
    )
    if question is not None:
        await _ask_question(message, case.id, question, state)


@router.callback_query(F.data.startswith("legal:start:"))
async def start_assessment(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await safe_callback_answer(callback)
    if callback.data is None or callback.message is None:
        return
    try:
        case_id = int(callback.data.rpartition(":")[2])
    except ValueError:
        return

    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await safe_answer(callback.message, "Дело не найдено.")
        return

    await begin_legal_assessment_for_case_message(
        callback.message,
        case,
        state,
        session,
    )


@router.callback_query(F.data.startswith("legal:restart:"))
async def restart_assessment(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await safe_callback_answer(callback)
    if callback.data is None or callback.message is None:
        return
    try:
        case_id = int(callback.data.rpartition(":")[2])
    except ValueError:
        return
    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await safe_answer(callback.message, "Дело не найдено.")
        return
    assessment = await LegalAssessmentService(session).start_with_context(
        case.id,
        violation_datetime=case.fine_notice.violation_datetime if case.fine_notice else None,
        notice_date=case.fine_notice.notice_date if case.fine_notice else None,
        complaint_recipient=(
            case.fine_notice.issuing_authority if case.fine_notice else None
        ),
        restart=True,
    )

    question = get_next_question(
        assessment.answers,
        case.fine_notice.article if case.fine_notice else None,
        _latest_ocr_text(case),
        case.fine_notice.violation_place if case.fine_notice else None,
    )
    if question is not None:
        await _ask_question(callback.message, case.id, question, state)


@router.callback_query(F.data.startswith("legal:answer:"))
async def answer_question(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.data is None or callback.message is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 5 or parts[0:2] != ["legal", "answer"]:
        await safe_callback_answer(callback, "Некорректный ответ", show_alert=True)
        return
    _, _, case_value, question_id, value = parts
    try:
        case_id = int(case_value)
    except ValueError:
        return

    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await safe_callback_answer(callback, "Дело не найдено", show_alert=True)
        return
    assessment = await LegalAssessmentService(session).get_for_case(case.id)
    if assessment is None:
        await safe_callback_answer(callback, "Начните анкету заново", show_alert=True)
        return

    article, ocr_text, violation_place = _case_context(case)
    try:
        next_question = await LegalAssessmentService(session).answer(
            assessment,
            question_id,
            value,
            article,
            ocr_text,
            violation_place,
        )
    except ValueError:
        await safe_callback_answer(
            callback, "Этот вопрос уже обработан", show_alert=True
        )
        return
    await safe_callback_answer(callback)
    if next_question is not None:
        await _ask_question(callback.message, case.id, next_question, state)
        return
    await safe_answer(
        callback.message,
        _result_text(assessment),
        reply_markup=_result_keyboard(case.id),
    )


@router.callback_query(F.data.startswith("ai:start:"))
async def start_ai_analysis(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await safe_callback_answer(callback)
    if callback.data is None or callback.message is None:
        return
    try:
        case_id = int(callback.data.rpartition(":")[2])
    except ValueError:
        return
    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await safe_answer(callback.message, "Дело не найдено.")
        return
    await safe_answer(callback.message, "Выполняю анализ дела с помощью ИИ. Это может занять до минуты.")
    try:
        analysis = await LegalAnalysisService(session).analyze_case(case.id)
        await session.commit()
    except Exception:
        logger.exception("Stage 4 AI analysis failed for case %s", case.id)
        await session.rollback()
        await safe_answer(callback.message, "Не удалось выполнить анализ. Попробуйте повторить позже.")
        return
    await safe_answer(
        callback.message,
        _analysis_text(analysis),
        reply_markup=_analysis_keyboard(case.id, analysis),
    )


@router.callback_query(F.data.startswith("ai:ground:"))
async def confirm_ai_ground(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await safe_callback_answer(callback)
    if callback.data is None or callback.message is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 5:
        return
    _, _, case_value, ground_id, action = parts
    try:
        case_id = int(case_value)
    except ValueError:
        return
    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await safe_answer(callback.message, "Дело не найдено.")
        return
    status = (
        LegalGroundStatus.CONFIRMED
        if action == "confirm"
        else LegalGroundStatus.REJECTED
    )
    try:
        analysis = await LegalAnalysisService(session).set_ground_status(
            case.id, ground_id, status
        )
        await session.commit()
    except ValueError:
        await safe_answer(callback.message, "Основание не найдено.")
        return
    await safe_answer(
        callback.message,
        _analysis_text(analysis),
        reply_markup=_analysis_keyboard(case.id, analysis),
    )


@router.callback_query(F.data.startswith("ai:docs:"))
async def generate_ai_documents(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await safe_callback_answer(callback)
    if callback.data is None or callback.message is None:
        return
    try:
        case_id = int(callback.data.rpartition(":")[2])
    except ValueError:
        return
    case = await _case_for_callback(callback, case_id, session)
    if case is None:
        await safe_answer(callback.message, "Дело не найдено.")
        return
    await safe_answer(callback.message, "Готовлю жалобу и ходатайство, если оно нужно.")
    try:
        documents = await LegalAnalysisService(session).generate_documents(case.id)
        await session.commit()
    except ValueError as exc:
        await safe_answer(callback.message, str(exc))
        return
    except Exception:
        logger.exception("Stage 4 document generation failed for case %s", case.id)
        await session.rollback()
        await safe_answer(callback.message, "Не удалось подготовить документы. Попробуйте повторить позже.")
        return

    confirmed = case.legal_analysis.grounds if case.legal_analysis else []
    missing_count = len(case.legal_analysis.missing_evidence) if case.legal_analysis else 0
    await safe_answer(
        callback.message,
        "Документы готовы.\n\n"
        f"Подтверждено оснований: {sum(1 for item in confirmed if item.get('status') == LegalGroundStatus.CONFIRMED.value)}\n"
        f"Необходимы дополнительные доказательства: {missing_count}",
        reply_markup=main_menu_keyboard(),
    )
    for document in documents:
        if document.file_format in {GeneratedDocumentFormat.DOCX, GeneratedDocumentFormat.PDF}:
            await callback.message.answer_document(
                FSInputFile(generated_file_path(document), filename=document.original_filename)
            )


@router.message(LegalQuestionnaire.waiting_for_answer)
async def answer_date_question(
    message, state: FSMContext, session: AsyncSession
) -> None:
    if message.from_user is None:
        return
    text = message.text or ""
    if text in {CHECK_FINE_TEXT, MY_CASES_TEXT, HELP_TEXT}:
        data = await state.get_data()
        question = get_question(str(data.get("question_id") or ""))
        if question is not None:
            await safe_answer(
                message,
                "Сначала ответьте на текущий вопрос анкеты.\n\n"
                f"Юридическая анкета по делу №{data.get('case_id')}\n\n"
                f"{question.text}"
            )
            return
    data = await state.get_data()
    case_id = data.get("case_id")
    question_id = data.get("question_id")
    if not case_id or not question_id:
        await state.clear()
        await safe_answer(message, "Анкета устарела. Начните заново.")
        return

    try:
        case_id = int(case_id)
    except ValueError:
        await state.clear()
        await safe_answer(message, "Анкета устарела. Начните заново.")
        return

    case = await _case_for_telegram_user(session, message.from_user.id, case_id)
    if case is None:
        await state.clear()
        await safe_answer(message, "Дело не найдено.")
        return

    assessment = await LegalAssessmentService(session).get_for_case(case.id)
    if assessment is None:
        await state.clear()
        await safe_answer(message, "Анкета ещё не начата.")
        return

    article, ocr_text, violation_place = _case_context(case)
    try:
        next_question = await LegalAssessmentService(session).answer(
            assessment,
            str(question_id),
            message.text or "",
            article,
            ocr_text,
            violation_place,
        )
    except ValueError:
        question = get_question(str(question_id))
        if question is not None and question.input_kind == "date":
            await safe_answer(message, "Отправьте дату в формате ДД.ММ.ГГГГ.")
        elif question is not None and question.input_kind == "text":
            await safe_answer(message, "Отправьте адрес текстом, минимум 5 символов.")
        else:
            await safe_answer(message, "Ответ не подходит для текущего вопроса.")
        return

    if next_question is not None:
        await _ask_question(message, case.id, next_question, state)
        return

    await state.clear()
    await safe_answer(
        message, _result_text(assessment), reply_markup=_result_keyboard(case.id)
    )
