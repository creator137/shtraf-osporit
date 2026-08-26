import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.admin as admin_api
from app.db.models import CaseStatus
from app.api.admin import get_session
from app.api.main import app
from app.db.models import Document
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
async def test_delete_is_allowed_by_cors(api_client: AsyncClient) -> None:
    response = await api_client.options(
        "/admin/cases/3",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-methods"] == "GET, PATCH, DELETE"


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
    document = await DocumentService(db_session).create(
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


@pytest.mark.asyncio
async def test_update_case_status(api_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_004, None, "Status", "Owner"
    )
    case = await CaseService(db_session).create(user.id)

    response = await api_client.patch(
        f"/admin/cases/{case.id}/status",
        json={"status": CaseStatus.IN_PROGRESS.value},
    )

    assert response.status_code == 200
    assert response.json()["status"] == CaseStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_delete_case_removes_case_documents(
    api_client: AsyncClient, db_session: AsyncSession, tmp_path
) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_006, None, "Delete", "Owner"
    )
    case = await CaseService(db_session).create(user.id)
    relative_path = "storage/cases/delete/document.pdf"
    file_path = tmp_path / relative_path
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"delete me")
    document = await DocumentService(db_session).create(
        case=case,
        telegram_file_id="delete-file",
        original_filename="document.pdf",
        mime_type="application/pdf",
        local_path=relative_path,
    )
    original_root = admin_api.BACKEND_ROOT
    admin_api.BACKEND_ROOT = tmp_path
    try:
        response = await api_client.delete(f"/admin/cases/{case.id}")
    finally:
        admin_api.BACKEND_ROOT = original_root

    assert response.status_code == 204
    assert not file_path.exists()
    assert await db_session.scalar(select(Document).where(Document.id == document.id)) is None
    assert (await api_client.get(f"/admin/cases/{case.id}")).status_code == 404


@pytest.mark.asyncio
async def test_document_file(api_client: AsyncClient, db_session: AsyncSession, tmp_path) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_005, None, "File", "Owner"
    )
    case = await CaseService(db_session).create(user.id)
    relative_path = "storage/cases/test/document.pdf"
    file_path = tmp_path / relative_path
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"test document")
    document = await DocumentService(db_session).create(
        case=case,
        telegram_file_id="file-route-test",
        original_filename="document.pdf",
        mime_type="application/pdf",
        local_path=relative_path,
    )
    original_root = admin_api.BACKEND_ROOT
    admin_api.BACKEND_ROOT = tmp_path
    try:
        response = await api_client.get(f"/admin/documents/{document.id}/file")
    finally:
        admin_api.BACKEND_ROOT = original_root

    assert response.status_code == 200
    assert response.content == b"test document"
