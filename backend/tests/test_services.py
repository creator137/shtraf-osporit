import asyncio

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CaseStatus, User
from app.db.session import async_session_factory
from app.services.case_service import CaseService
from app.services.document_service import DocumentService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_user_registration_is_idempotent(db_session: AsyncSession) -> None:
    service = UserService(db_session)

    first = await service.get_or_create(100_000_001, "first", "Test", None)
    second = await service.get_or_create(100_000_001, "updated", "Test", "User")

    count = await db_session.scalar(
        select(func.count(User.id)).where(User.telegram_id == 100_000_001)
    )
    assert first.id == second.id
    assert second.username == "updated"
    assert count == 1


@pytest.mark.asyncio
async def test_concurrent_user_registration_is_idempotent() -> None:
    telegram_id = 9_999_999_999_999

    async def register(username: str) -> int:
        async with async_session_factory() as session:
            user = await UserService(session).get_or_create(
                telegram_id, username, "Concurrent", "User"
            )
            await session.commit()
            return user.id

    try:
        first_id, second_id = await asyncio.gather(
            register("first"), register("second")
        )
        async with async_session_factory() as session:
            count = await session.scalar(
                select(func.count(User.id)).where(User.telegram_id == telegram_id)
            )

        assert first_id == second_id
        assert count == 1
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.telegram_id == telegram_id))
            await session.commit()


@pytest.mark.asyncio
async def test_case_is_linked_to_user(db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        100_000_002, None, "Case", "Owner"
    )

    case = await CaseService(db_session).create(user.id)
    cases = await CaseService(db_session).list_for_user(user.id)

    assert case.user_id == user.id
    assert [item.id for item in cases] == [case.id]


@pytest.mark.asyncio
async def test_document_is_linked_to_case(db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        100_000_003, None, "Document", "Owner"
    )
    case = await CaseService(db_session).create(user.id)

    document = await DocumentService(db_session).create(
        case=case,
        telegram_file_id="test-file-id",
        original_filename="synthetic.pdf",
        mime_type="application/pdf",
        local_path="storage/cases/test/synthetic.pdf",
    )
    loaded_case = await CaseService(db_session).get_for_user(user.id, case.id)

    assert document.case_id == case.id
    assert loaded_case is not None
    assert loaded_case.status is CaseStatus.DOCUMENT_UPLOADED
    assert [item.id for item in loaded_case.documents] == [document.id]
