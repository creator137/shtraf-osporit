import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import get_session
from app.api.main import app
from app.services.case_service import CaseService
from app.services.document_service import DocumentService
from app.services.user_service import UserService


@pytest.fixture
async def api_client(db_session: AsyncSession):
    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_users(api_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_001, "admin_test", "Test", "User"
    )
    await CaseService(db_session).create(user.id)

    response = await api_client.get("/admin/users")

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == user.id)
    assert item["telegram_id"] == 200_000_001
    assert item["cases_count"] == 1


@pytest.mark.asyncio
async def test_list_cases(api_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_002, None, "Case", "Owner"
    )
    case = await CaseService(db_session).create(user.id)
    await DocumentService(db_session).create(
        case=case,
        telegram_file_id="admin-list-file",
        original_filename="synthetic.pdf",
        mime_type="application/pdf",
        local_path="storage/cases/test/synthetic.pdf",
    )

    response = await api_client.get("/admin/cases")

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == case.id)
    assert item["documents_count"] == 1
    assert item["user"]["telegram_id"] == 200_000_002


@pytest.mark.asyncio
async def test_case_detail(api_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_003, "detail_test", "Detail", "Owner"
    )
    case = await CaseService(db_session).create(user.id)
    document = await DocumentService(db_session).create(
        case=case,
        telegram_file_id="admin-detail-file",
        original_filename="notice.jpg",
        mime_type="image/jpeg",
        local_path="storage/cases/test/notice.jpg",
    )

    response = await api_client.get(f"/admin/cases/{case.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["username"] == "detail_test"
    assert payload["documents"][0]["id"] == document.id
    assert "local_path" not in payload["documents"][0]

    missing = await api_client.get("/admin/cases/999999999")
    assert missing.status_code == 404
