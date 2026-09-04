from collections.abc import AsyncIterator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.application import create_bot
from app.config import get_settings
from app.db.models import (
    Case,
    CaseStatus,
    Document,
    DocumentRecognition,
    FineNotice,
    GeneratedDocument,
    LegalAssessment,
    LegalAssessmentStatus,
    LegalAnalysis,
    RecognitionStatus,
    User,
    UserConsent,
)
from app.db.session import async_session_factory
from app.offers import OFFERS
from app.services.case_service import CaseService
from app.services.document_service import BACKEND_ROOT, remove_local_document_file
from app.services.extraction_service import FineNoticeFields
from app.services.legal_rules import (
    LEGAL_SOURCES,
    QUESTIONS,
    RULE_VERSIONS,
    RULES,
    answer_label,
    get_question,
    serialize_rule,
)
from app.services.ocr_service import create_ocr_provider
from app.services.payment_intent_service import PaymentIntentService
from app.services.recognition_service import RecognitionService

router = APIRouter(prefix="/admin", tags=["admin"])


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


class UserSummary(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None


class UserListItem(UserSummary):
    id: int
    created_at: datetime
    cases_count: int
    consent_version: str | None
    consent_accepted_at: datetime | None


class CaseListItem(BaseModel):
    id: int
    status: CaseStatus
    created_at: datetime
    user: UserSummary
    documents_count: int
    recognition_status: RecognitionStatus | None
    notice_number: str | None
    fine_amount: int | None
    recognized_fields_count: int
    legal_assessment_status: LegalAssessmentStatus | None


class DocumentItem(BaseModel):
    id: int
    original_filename: str | None
    mime_type: str | None
    created_at: datetime


class RecognitionItem(BaseModel):
    id: int
    document_id: int
    status: RecognitionStatus
    raw_text: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class FineNoticeItem(BaseModel):
    notice_number: str | None
    notice_date: str | None
    uin: str | None
    fine_amount: int | None
    article: str | None
    vehicle_plate: str | None
    violation_datetime: str | None
    violation_place: str | None
    issuing_authority: str | None


class LegalAnswerItem(BaseModel):
    question_id: str
    question: str
    value: str
    answer: str


class LegalAssessmentItem(BaseModel):
    status: LegalAssessmentStatus
    rules_version: str
    answers: list[LegalAnswerItem]
    results: list[dict[str, object]]
    completed_at: datetime | None
    updated_at: datetime


class LegalRuleItem(BaseModel):
    code: str
    title: str
    direction: str
    legal_basis: str
    required_evidence: list[str]
    source_ids: list[str]


class LegalEvidenceItem(BaseModel):
    name: str
    status: str


class LegalRuleVersionItem(BaseModel):
    version: str
    effective_from: str
    title: str


class LegalSourceItem(BaseModel):
    id: str
    title: str
    reference: str
    effective_note: str
    document_available: bool


class LegalKnowledgeBase(BaseModel):
    rules: list[LegalRuleItem]
    versions: list[LegalRuleVersionItem]
    sources: list[LegalSourceItem]


class LegalAnalysisItem(BaseModel):
    status: str
    provider: str
    model: str
    summary: str | None
    overall_assessment: str | None
    grounds: list[dict[str, object]]
    missing_evidence: list[str]
    document_evidence_review: dict[str, object] | None
    created_at: datetime
    updated_at: datetime


class GeneratedDocumentItem(BaseModel):
    id: int
    document_type: str
    file_format: str
    original_filename: str
    created_at: datetime


class PaymentOfferStatsItem(BaseModel):
    offer_code: str
    title: str
    description: str
    price: str
    clicks: int
    unique_users: int


class PaymentIntentStatsItem(BaseModel):
    total_clicks: int
    unique_users: int
    unique_cases: int
    offers: list[PaymentOfferStatsItem]


class PaymentIntentItem(BaseModel):
    id: int
    created_at: datetime
    user_id: int
    user: UserSummary
    case_id: int | None
    offer_code: str
    offer_title: str
    price: str


class CaseDetail(BaseModel):
    id: int
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    user: UserSummary
    documents: list[DocumentItem]
    recognition: RecognitionItem | None
    fine_notice: FineNoticeItem | None
    recognized_fields_count: int
    legal_assessment: LegalAssessmentItem | None
    legal_analysis: LegalAnalysisItem | None
    generated_documents: list[GeneratedDocumentItem]


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class FineNoticeUpdate(BaseModel):
    notice_number: str | None = Field(default=None, max_length=100)
    notice_date: str | None = Field(default=None, max_length=50)
    uin: str | None = Field(default=None, max_length=64)
    fine_amount: int | None = Field(default=None, ge=0)
    article: str | None = Field(default=None, max_length=255)
    vehicle_plate: str | None = Field(default=None, max_length=32)
    violation_datetime: str | None = Field(default=None, max_length=100)
    violation_place: str | None = Field(default=None, max_length=2_000)
    issuing_authority: str | None = Field(default=None, max_length=1_000)


def user_summary(user: User) -> UserSummary:
    return UserSummary(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    session: AsyncSession = Depends(get_session),
) -> list[UserListItem]:
    cases_count = (
        select(func.count(Case.id))
        .where(Case.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    consent_version = (
        select(UserConsent.version)
        .where(UserConsent.user_id == User.id)
        .order_by(desc(UserConsent.accepted_at))
        .limit(1)
        .correlate(User)
        .scalar_subquery()
    )
    consent_accepted_at = (
        select(UserConsent.accepted_at)
        .where(UserConsent.user_id == User.id)
        .order_by(desc(UserConsent.accepted_at))
        .limit(1)
        .correlate(User)
        .scalar_subquery()
    )
    rows = await session.execute(
        select(
            User,
            cases_count.label("cases_count"),
            consent_version.label("consent_version"),
            consent_accepted_at.label("consent_accepted_at"),
        )
        .order_by(desc(User.created_at))
        .limit(100)
    )
    return [
        UserListItem(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
            cases_count=case_count,
            consent_version=consent_ver,
            consent_accepted_at=consent_at,
        )
        for user, case_count, consent_ver, consent_at in rows
    ]


@router.get("/payment-intents/stats", response_model=PaymentIntentStatsItem)
async def payment_intent_stats(
    session: AsyncSession = Depends(get_session),
) -> PaymentIntentStatsItem:
    stats = await PaymentIntentService(session).stats()
    return PaymentIntentStatsItem(
        total_clicks=stats.total_clicks,
        unique_users=stats.unique_users,
        unique_cases=stats.unique_cases,
        offers=[
            PaymentOfferStatsItem(
                offer_code=item.offer_code,
                title=OFFERS[item.offer_code].title,
                description=OFFERS[item.offer_code].description,
                price=OFFERS[item.offer_code].price,
                clicks=item.clicks,
                unique_users=item.unique_users,
            )
            for item in stats.offers
        ],
    )


@router.get("/payment-intents", response_model=list[PaymentIntentItem])
async def list_payment_intents(
    session: AsyncSession = Depends(get_session),
) -> list[PaymentIntentItem]:
    intents = await PaymentIntentService(session).list_recent(limit=100)
    return [
        PaymentIntentItem(
            id=intent.id,
            created_at=intent.created_at,
            user_id=intent.user_id,
            user=user_summary(intent.user),
            case_id=intent.case_id,
            offer_code=intent.offer_code,
            offer_title=OFFERS[intent.offer_code].title,
            price=OFFERS[intent.offer_code].price,
        )
        for intent in intents
        if intent.offer_code in OFFERS
    ]


@router.get("/cases", response_model=list[CaseListItem])
async def list_cases(session: AsyncSession = Depends(get_session)) -> list[CaseListItem]:
    cases = await session.scalars(
        select(Case)
        .options(
            selectinload(Case.user),
            selectinload(Case.documents).selectinload(Document.recognition),
            selectinload(Case.fine_notice),
            selectinload(Case.legal_assessment),
            selectinload(Case.legal_analysis),
            selectinload(Case.generated_documents),
        )
        .order_by(desc(Case.created_at))
        .limit(100)
    )
    return [
        CaseListItem(
            id=case.id,
            status=case.status,
            created_at=case.created_at,
            user=user_summary(case.user),
            documents_count=len(case.documents),
            recognition_status=(
                recognition.status
                if (recognition := _latest_recognition(case.documents))
                else None
            ),
            notice_number=case.fine_notice.notice_number if case.fine_notice else None,
            fine_amount=case.fine_notice.fine_amount if case.fine_notice else None,
            recognized_fields_count=_recognized_fields_count(case.fine_notice),
            legal_assessment_status=(
                case.legal_assessment.status if case.legal_assessment else None
            ),
        )
        for case in cases
    ]


@router.get("/cases/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: int, session: AsyncSession = Depends(get_session)
) -> CaseDetail:
    case = await session.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.user),
            selectinload(Case.documents).selectinload(Document.recognition),
            selectinload(Case.fine_notice),
            selectinload(Case.legal_assessment),
            selectinload(Case.legal_analysis),
            selectinload(Case.generated_documents),
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    recognition = _latest_recognition(case.documents)
    return CaseDetail(
        id=case.id,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
        user=user_summary(case.user),
        documents=[
            DocumentItem(
                id=document.id,
                original_filename=document.original_filename,
                mime_type=document.mime_type,
                created_at=document.created_at,
            )
            for document in case.documents
        ],
        recognition=recognition_item(recognition),
        fine_notice=fine_notice_item(case.fine_notice),
        recognized_fields_count=_recognized_fields_count(case.fine_notice),
        legal_assessment=legal_assessment_item(case.legal_assessment),
        legal_analysis=legal_analysis_item(case.legal_analysis),
        generated_documents=[
            GeneratedDocumentItem(
                id=document.id,
                document_type=document.document_type.value,
                file_format=document.file_format.value,
                original_filename=document.original_filename,
                created_at=document.created_at,
            )
            for document in sorted(
                case.generated_documents, key=lambda item: item.created_at, reverse=True
            )
        ],
    )


@router.get("/legal-rules", response_model=LegalKnowledgeBase)
async def get_legal_rules() -> LegalKnowledgeBase:
    return LegalKnowledgeBase(
        rules=[LegalRuleItem(**serialize_rule(rule)) for rule in RULES],
        versions=[LegalRuleVersionItem(**item) for item in RULE_VERSIONS],
        sources=[LegalSourceItem(**source) for source in LEGAL_SOURCES],
    )


@router.get("/legal-sources/plenum-vs-20/file", response_model=None)
async def get_plenum_source_file() -> FileResponse:
    source_path = BACKEND_ROOT.parent / "docs" / "legal-sources" / "plenum-vs-rf-20-2019.pdf"
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Legal source file not found")
    return FileResponse(
        source_path,
        media_type="application/pdf",
        filename="plenum-vs-rf-20-2019.pdf",
    )


@router.patch("/cases/{case_id}/status", response_model=CaseDetail)
async def update_case_status(
    case_id: int,
    payload: CaseStatusUpdate,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    case = await session.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.user), selectinload(Case.documents))
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    await CaseService(session).update_status(case, payload.status)
    await session.commit()
    return await get_case(case_id, session)


@router.patch("/cases/{case_id}/fine-notice", response_model=CaseDetail)
async def update_fine_notice(
    case_id: int,
    payload: FineNoticeUpdate,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    exists = await session.scalar(select(Case.id).where(Case.id == case_id))
    if exists is None:
        raise HTTPException(status_code=404, detail="Case not found")

    await RecognitionService(session).update_notice(
        case_id,
        FineNoticeFields(
            notice_number=payload.notice_number,
            notice_date=payload.notice_date,
            uin=payload.uin,
            fine_amount=payload.fine_amount,
            article=payload.article,
            vehicle_plate=payload.vehicle_plate,
            violation_datetime=payload.violation_datetime,
            violation_place=payload.violation_place,
            issuing_authority=payload.issuing_authority,
        ),
    )
    await session.commit()
    return await get_case(case_id, session)


@router.post("/cases/{case_id}/send-questionnaire", status_code=204)
async def send_questionnaire_to_client(
    case_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    case = await session.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.user))
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    bot = create_bot(get_settings())
    try:
        await bot.send_message(
            chat_id=case.user.telegram_id,
            text=(
                f"По делу №{case.id} нужно заполнить юридическую анкету.\n\n"
                "Ответьте на несколько вопросов о постановлении, чтобы система "
                "определила направления дальнейшей проверки."
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Пройти юридическую анкету",
                            callback_data=f"legal:start:{case.id}",
                        )
                    ]
                ]
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Не удалось отправить анкету в Telegram.",
        ) from exc
    finally:
        await bot.session.close()

    return Response(status_code=204)


@router.post("/cases/{case_id}/recognize", response_model=CaseDetail)
async def recognize_case_document(
    case_id: int,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    case = await session.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.documents))
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.documents:
        raise HTTPException(status_code=404, detail="Case document not found")

    document = max(case.documents, key=lambda item: item.created_at)
    recognition = await session.scalar(
        select(DocumentRecognition).where(
            DocumentRecognition.document_id == document.id
        )
    )
    if (
        recognition is not None
        and recognition.status is RecognitionStatus.VERIFIED
    ):
        raise HTTPException(
            status_code=409,
            detail="Verified recognition cannot be overwritten",
        )
    content = await document_content(document)
    await RecognitionService(session).process_document(
        case.id,
        document,
        content,
        create_ocr_provider(get_settings()),
    )
    await session.commit()
    return await get_case(case_id, session)


@router.delete("/cases/{case_id}", status_code=204)
async def delete_case(
    case_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    case = await session.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.documents))
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    for document in case.documents:
        remove_local_document_file(document)

    await session.delete(case)
    await session.commit()
    return Response(status_code=204)


@router.get("/documents/{document_id}/file", response_model=None)
async def get_document_file(
    document_id: int, session: AsyncSession = Depends(get_session)
) -> FileResponse | Response:
    document = await session.scalar(select(Document).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.local_path:
        file_path = (BACKEND_ROOT / document.local_path).resolve()
        storage_root = (BACKEND_ROOT / "storage").resolve()
        if storage_root in file_path.parents and file_path.is_file():
            return FileResponse(
                path=file_path,
                media_type=document.mime_type or "application/octet-stream",
                filename=document.original_filename or Path(file_path).name,
            )

    if not document.telegram_file_id:
        raise HTTPException(status_code=404, detail="Document file not found")

    bot = create_bot(get_settings())
    destination = BytesIO()
    try:
        telegram_file = await bot.get_file(document.telegram_file_id)
        if telegram_file.file_path is None:
            raise HTTPException(status_code=404, detail="Document file not found")
        await bot.download_file(telegram_file.file_path, destination=destination)
    finally:
        await bot.session.close()

    filename = document.original_filename or f"document-{document.id}"
    return Response(
        content=destination.getvalue(),
        media_type=document.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get("/generated-documents/{document_id}/file", response_model=None)
async def get_generated_document_file(
    document_id: int, session: AsyncSession = Depends(get_session)
) -> FileResponse:
    document = await session.scalar(
        select(GeneratedDocument).where(GeneratedDocument.id == document_id)
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Generated document not found")
    file_path = (BACKEND_ROOT / document.file_path).resolve()
    storage_root = (BACKEND_ROOT / "storage").resolve()
    if storage_root not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Generated document file not found")
    media_type = (
        "application/pdf"
        if document.file_format.value == "PDF"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=document.original_filename,
    )


async def document_content(document: Document) -> bytes:
    if document.local_path:
        file_path = (BACKEND_ROOT / document.local_path).resolve()
        storage_root = (BACKEND_ROOT / "storage").resolve()
        if storage_root in file_path.parents and file_path.is_file():
            return file_path.read_bytes()

    if not document.telegram_file_id:
        raise HTTPException(status_code=404, detail="Document file not found")

    bot = create_bot(get_settings())
    destination = BytesIO()
    try:
        telegram_file = await bot.get_file(document.telegram_file_id)
        if telegram_file.file_path is None:
            raise HTTPException(status_code=404, detail="Document file not found")
        await bot.download_file(telegram_file.file_path, destination=destination)
    finally:
        await bot.session.close()
    return destination.getvalue()


def _latest_recognition(documents: list[Document]) -> DocumentRecognition | None:
    recognitions = [
        document.recognition
        for document in documents
        if document.recognition is not None
    ]
    return max(recognitions, key=lambda item: item.created_at) if recognitions else None


def recognition_item(
    recognition: DocumentRecognition | None,
) -> RecognitionItem | None:
    if recognition is None:
        return None
    return RecognitionItem(
        id=recognition.id,
        document_id=recognition.document_id,
        status=recognition.status,
        raw_text=recognition.raw_text,
        error_message=recognition.error_message,
        created_at=recognition.created_at,
        updated_at=recognition.updated_at,
    )


def fine_notice_item(notice: FineNotice | None) -> FineNoticeItem | None:
    if notice is None:
        return None
    return FineNoticeItem(
        notice_number=notice.notice_number,
        notice_date=notice.notice_date,
        uin=notice.uin,
        fine_amount=notice.fine_amount,
        article=notice.article,
        vehicle_plate=notice.vehicle_plate,
        violation_datetime=notice.violation_datetime,
        violation_place=notice.violation_place,
        issuing_authority=notice.issuing_authority,
    )


def legal_assessment_item(
    assessment: LegalAssessment | None,
) -> LegalAssessmentItem | None:
    if assessment is None:
        return None
    answers = []
    ordered_question_ids = [
        question.id for question in QUESTIONS if question.id in assessment.answers
    ]
    ordered_question_ids.extend(
        question_id
        for question_id in assessment.answers
        if question_id not in ordered_question_ids
    )
    for question_id in ordered_question_ids:
        value = assessment.answers[question_id]
        question = get_question(question_id)
        answers.append(
            LegalAnswerItem(
                question_id=question_id,
                question=question.text if question else question_id,
                value=value,
                answer=answer_label(question_id, value),
            )
        )
    return LegalAssessmentItem(
        status=assessment.status,
        rules_version=assessment.rules_version,
        answers=answers,
        results=assessment.results,
        completed_at=assessment.completed_at,
        updated_at=assessment.updated_at,
    )


def legal_analysis_item(analysis: LegalAnalysis | None) -> LegalAnalysisItem | None:
    if analysis is None:
        return None
    result = analysis.result or {}
    return LegalAnalysisItem(
        status=analysis.status.value,
        provider=analysis.provider,
        model=analysis.model,
        summary=result.get("summary") if isinstance(result.get("summary"), str) else None,
        overall_assessment=(
            result.get("overall_assessment")
            if isinstance(result.get("overall_assessment"), str)
            else None
        ),
        grounds=analysis.grounds,
        missing_evidence=analysis.missing_evidence,
        document_evidence_review=(
            result.get("document_evidence_review")
            if isinstance(result.get("document_evidence_review"), dict)
            else None
        ),
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


def _recognized_fields_count(notice: FineNotice | None) -> int:
    if notice is None:
        return 0
    fields = (
        notice.notice_number,
        notice.notice_date,
        notice.uin,
        notice.fine_amount,
        notice.article,
        notice.vehicle_plate,
        notice.violation_datetime,
        notice.violation_place,
        notice.issuing_authority,
    )
    return sum(value is not None and value != "" for value in fields)
