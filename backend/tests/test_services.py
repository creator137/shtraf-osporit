from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db.models import CaseStatus, User
from app.services.case_service import CaseService
from app.services.document_service import DocumentService
from app.services.user_service import UserService


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    test_engine = create_async_engine(
        str(get_settings().database_url), poolclass=NullPool
    )
    try:
        async with test_engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    finally:
        await test_engine.dispose()


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
