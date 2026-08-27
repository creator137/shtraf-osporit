from collections.abc import AsyncIterator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
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
    RecognitionStatus,
    User,
    UserConsent,
)
from app.db.session import async_session_factory
from app.services.case_service import CaseService
from app.services.document_service import BACKEND_ROOT
from app.services.extraction_service import FineNoticeFields
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


class CaseDetail(BaseModel):
    id: int
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    user: UserSummary
    documents: list[DocumentItem]
    recognition: RecognitionItem | None
    fine_notice: FineNoticeItem | None


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class FineNoticeUpdate(BaseModel):
    notice_number: str | None = None
    notice_date: str | None = None
    uin: str | None = None
    fine_amount: int | None = None
    article: str | None = None
    vehicle_plate: str | None = None
    violation_datetime: str | None = None
    violation_place: str | None = None
    issuing_authority: str | None = None


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


@router.get("/cases", response_model=list[CaseListItem])
async def list_cases(session: AsyncSession = Depends(get_session)) -> list[CaseListItem]:
    documents_count = (
        select(func.count(Document.id))
        .where(Document.case_id == Case.id)
        .correlate(Case)
        .scalar_subquery()
    )
    rows = await session.execute(
        select(Case, documents_count.label("documents_count"))
        .options(selectinload(Case.user))
        .order_by(desc(Case.created_at))
        .limit(100)
    )
    return [
        CaseListItem(
            id=case.id,
            status=case.status,
            created_at=case.created_at,
            user=user_summary(case.user),
            documents_count=document_count,
        )
        for case, document_count in rows
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

    storage_root = (BACKEND_ROOT / "storage").resolve()
    for document in case.documents:
        if not document.local_path:
            continue
        file_path = (BACKEND_ROOT / document.local_path).resolve()
        if storage_root in file_path.parents:
            file_path.unlink(missing_ok=True)

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
