from types import SimpleNamespace
from unittest.mock import AsyncMock

import app.api.admin as admin_api
import app.services.document_service as document_service_module
import pytest
from app.api.admin import get_session
from app.api.main import app
from app.config import get_settings
from app.db.models import CaseStatus, Document, RecognitionStatus
from app.services.case_service import CaseService
from app.services.consent_service import (
    PERSONAL_DATA_CONSENT_VERSION,
    ConsentService,
)
from app.services.document_service import DocumentService
from app.services.legal_assessment_service import LegalAssessmentService
from app.services.legal_rules import get_next_question
from app.services.ocr_service import OcrResult
from app.services.user_service import UserService
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


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
            "Origin": get_settings().admin_origin,
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-methods"] == "GET, POST, PATCH, DELETE"


@pytest.mark.asyncio
async def test_list_users(api_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_001, "admin_test", "Test", "User"
    )
    await CaseService(db_session).create(user.id)
    await ConsentService(db_session).accept_current(user)

    response = await api_client.get("/admin/users")

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == user.id)
    assert item["telegram_id"] == 200_000_001
    assert item["cases_count"] == 1
    assert item["consent_version"] == PERSONAL_DATA_CONSENT_VERSION
    assert item["consent_accepted_at"] is not None


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
    recognition = await admin_api.RecognitionService(
        db_session
    ).create_pending_for_document(case, document)
    await admin_api.RecognitionService(db_session).save_recognized_text(
        case.id,
        document.id,
        "Постановление № 18810177230801000123. Штраф 1500 руб.",
    )

    response = await api_client.get("/admin/cases")

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == case.id)
    assert item["documents_count"] == 1
    assert item["user"]["telegram_id"] == 200_000_002
    assert item["recognition_status"] == RecognitionStatus.RECOGNIZED.value
    assert item["notice_number"] == "18810177230801000123"
    assert item["fine_amount"] == 1500
    assert item["recognized_fields_count"] == 2
    assert recognition.status is RecognitionStatus.RECOGNIZED


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
    assert payload["recognition"] is None
    assert payload["fine_notice"] is None
    assert payload["legal_assessment"] is None

    missing = await api_client.get("/admin/cases/999999999")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_legal_rules_and_case_assessment_api(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    knowledge_response = await api_client.get("/admin/legal-rules")
    assert knowledge_response.status_code == 200
    knowledge = knowledge_response.json()
    assert {rule["code"] for rule in knowledge["rules"]} >= {"A01", "A12", "A17"}
    assert {version["version"] for version in knowledge["versions"]} >= {
        "2026-08-28",
        "2026-09-01",
    }
    assert next(
        source for source in knowledge["sources"] if source["id"] == "plenum-vs-20"
    )["document_available"] is True

    user = await UserService(db_session).get_or_create(
        200_000_020, None, "Assessment", "Owner"
    )
    case = await CaseService(db_session).create(user.id)
    service = LegalAssessmentService(db_session)
    assessment = await service.start(case.id)
    answers = {
        "appeal_received_at": "28.08.2026",
        "driver": "sold",
        "sale_docs": "yes",
        "vehicle_photo": "yes",
        "plate_photo": "yes",
        "place_time_match": "yes",
        "speed": "not_speed",
        "camera": "none",
        "sign": "none",
        "marking": "none",
        "owner_data_match": "yes",
        "previous_resolution": "no",
        "article_qualification": "no",
        "duplicate": "no",
        "emergency": "no",
    }
    while (question := get_next_question(assessment.answers)) is not None:
        await service.answer(assessment, question.id, answers[question.id])

    detail_response = await api_client.get(f"/admin/cases/{case.id}")
    assert detail_response.status_code == 200
    legal = detail_response.json()["legal_assessment"]
    assert legal["status"] == "COMPLETED"
    assert legal["results"][0]["code"] == "A02"
    assert legal["results"][0]["evidence_items"][0]["status"] == "AVAILABLE"
    assert next(item for item in legal["answers"] if item["question_id"] == "driver")[
        "answer"
    ] == "Автомобиль был продан"


@pytest.mark.asyncio
async def test_update_fine_notice(api_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_007, None, "Notice", "Owner"
    )
    case = await CaseService(db_session).create(user.id)

    response = await api_client.patch(
        f"/admin/cases/{case.id}/fine-notice",
        json={
            "notice_number": "18810177230801000123",
            "notice_date": "01.08.2026",
            "uin": "18810177230801000123456",
            "fine_amount": 1500,
            "article": "ст. 12.9",
            "vehicle_plate": "А123ВС77",
            "violation_datetime": "01.08.2026 12:30",
            "violation_place": "Москва, Тверская улица",
            "issuing_authority": "ЦАФАП",
        },
    )

    assert response.status_code == 200
    notice = response.json()["fine_notice"]
    assert notice["notice_number"] == "18810177230801000123"
    assert notice["fine_amount"] == 1500
    assert response.json()["status"] == CaseStatus.READY.value
    assert response.json()["recognized_fields_count"] == 9

    invalid = await api_client.patch(
        f"/admin/cases/{case.id}/fine-notice",
        json={"fine_amount": -1},
    )
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_recognize_case_document(
    api_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeOcrProvider:
        async def recognize(self, content: bytes, filename: str, mime_type: str | None):
            assert content == b"document-bytes"
            return OcrResult(
                text=(
                    "Постановление № 18810177230801000123. "
                    "УИН 18810177230801000123456. Штраф 1500 руб."
                )
            )

    async def fake_document_content(document: Document) -> bytes:
        return b"document-bytes"

    monkeypatch.setattr(admin_api, "document_content", fake_document_content)
    monkeypatch.setattr(
        admin_api, "create_ocr_provider", lambda settings: FakeOcrProvider()
    )
    user = await UserService(db_session).get_or_create(
        200_000_008, None, "Recognize", "Owner"
    )
    case = await CaseService(db_session).create(user.id)
    await DocumentService(db_session).create(
        case=case,
        telegram_file_id="recognize-file",
        original_filename="notice.jpg",
        mime_type="image/jpeg",
        local_path=None,
    )

    response = await api_client.post(f"/admin/cases/{case.id}/recognize")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recognition"]["status"] == "RECOGNIZED"
    assert payload["fine_notice"]["notice_number"] == "18810177230801000123"


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
async def test_send_questionnaire_to_client(
    api_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await UserService(db_session).get_or_create(
        200_000_008, "questionnaire_client", "Questionnaire", "Client"
    )
    case = await CaseService(db_session).create(user.id)
    bot = SimpleNamespace(
        send_message=AsyncMock(),
        session=SimpleNamespace(close=AsyncMock()),
    )
    monkeypatch.setattr(admin_api, "create_bot", lambda settings: bot)

    response = await api_client.post(f"/admin/cases/{case.id}/send-questionnaire")

    assert response.status_code == 204
    bot.send_message.assert_awaited_once()
    call = bot.send_message.await_args
    assert call.kwargs["chat_id"] == user.telegram_id
    assert f"делу №{case.id}" in call.kwargs["text"]
    assert (
        call.kwargs["reply_markup"].inline_keyboard[0][0].callback_data
        == f"legal:start:{case.id}"
    )
    bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_case_removes_case_documents(
    api_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setattr(document_service_module, "BACKEND_ROOT", tmp_path)
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
