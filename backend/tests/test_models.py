from sqlalchemy import inspect

from app.db.models import (
    Case,
    CaseStatus,
    Document,
    DocumentRecognition,
    FineNotice,
    LegalAssessment,
    PaymentIntent,
    User,
    UserConsent,
)


def test_models_are_registered() -> None:
    assert User.__tablename__ == "users"
    assert Case.__tablename__ == "cases"
    assert Document.__tablename__ == "documents"
    assert DocumentRecognition.__tablename__ == "document_recognitions"
    assert FineNotice.__tablename__ == "fine_notices"
    assert UserConsent.__tablename__ == "user_consents"
    assert LegalAssessment.__tablename__ == "legal_assessments"
    assert PaymentIntent.__tablename__ == "payment_intents"


def test_model_relationships() -> None:
    user_mapper = inspect(User)
    case_mapper = inspect(Case)

    assert user_mapper.relationships["cases"].mapper.class_ is Case
    assert user_mapper.relationships["consents"].mapper.class_ is UserConsent
    assert case_mapper.relationships["user"].mapper.class_ is User
    assert case_mapper.relationships["documents"].mapper.class_ is Document
    assert case_mapper.relationships["fine_notice"].mapper.class_ is FineNotice
    assert case_mapper.relationships["legal_assessment"].mapper.class_ is LegalAssessment
    assert user_mapper.relationships["payment_intents"].mapper.class_ is PaymentIntent
    assert case_mapper.relationships["payment_intents"].mapper.class_ is PaymentIntent
    assert inspect(Document).relationships["case"].mapper.class_ is Case
    assert (
        inspect(Document).relationships["recognition"].mapper.class_
        is DocumentRecognition
    )
    assert inspect(FineNotice).relationships["case"].mapper.class_ is Case
    assert inspect(UserConsent).relationships["user"].mapper.class_ is User


def test_model_constraints_and_defaults() -> None:
    telegram_id = inspect(User).columns.telegram_id
    case_user_id = inspect(Case).columns.user_id
    document_case_id = inspect(Document).columns.case_id
    recognition_document_id = inspect(DocumentRecognition).columns.document_id
    fine_notice_case_id = inspect(FineNotice).columns.case_id
    consent_user_id = inspect(UserConsent).columns.user_id
    legal_case_id = inspect(LegalAssessment).columns.case_id
    payment_user_id = inspect(PaymentIntent).columns.user_id
    payment_case_id = inspect(PaymentIntent).columns.case_id
    status = inspect(Case).columns.status

    assert telegram_id.unique is True
    assert next(iter(case_user_id.foreign_keys)).target_fullname == "users.id"
    assert next(iter(document_case_id.foreign_keys)).target_fullname == "cases.id"
    assert next(iter(recognition_document_id.foreign_keys)).target_fullname == "documents.id"
    assert next(iter(fine_notice_case_id.foreign_keys)).target_fullname == "cases.id"
    assert next(iter(consent_user_id.foreign_keys)).target_fullname == "users.id"
    assert next(iter(legal_case_id.foreign_keys)).target_fullname == "cases.id"
    assert legal_case_id.unique is True
    assert next(iter(payment_user_id.foreign_keys)).target_fullname == "users.id"
    assert next(iter(payment_case_id.foreign_keys)).target_fullname == "cases.id"
    assert payment_case_id.nullable is True
    assert status.default.arg is CaseStatus.DOCUMENT_UPLOADED
    assert str(status.server_default.arg) == CaseStatus.DOCUMENT_UPLOADED.value
