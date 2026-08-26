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
from app.db.models import Case, CaseStatus, Document, User
from app.db.session import async_session_factory
from app.services.case_service import CaseService
from app.services.document_service import BACKEND_ROOT


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


class CaseDetail(BaseModel):
    id: int
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    user: UserSummary
    documents: list[DocumentItem]


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


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
    rows = await session.execute(
        select(User, cases_count.label("cases_count"))
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
        )
        for user, case_count in rows
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
        .options(selectinload(Case.user), selectinload(Case.documents))
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

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
