from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Case, CaseStatus, Document, User
from app.db.session import async_session_factory


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
