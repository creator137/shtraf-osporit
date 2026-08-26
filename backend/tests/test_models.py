from sqlalchemy import inspect

from app.db.models import Case, CaseStatus, Document, User


def test_models_are_registered() -> None:
    assert User.__tablename__ == "users"
    assert Case.__tablename__ == "cases"
    assert Document.__tablename__ == "documents"


def test_model_relationships() -> None:
    user_mapper = inspect(User)
    case_mapper = inspect(Case)

    assert user_mapper.relationships["cases"].mapper.class_ is Case
    assert case_mapper.relationships["user"].mapper.class_ is User
    assert case_mapper.relationships["documents"].mapper.class_ is Document
    assert inspect(Document).relationships["case"].mapper.class_ is Case


def test_model_constraints_and_defaults() -> None:
    telegram_id = inspect(User).columns.telegram_id
    case_user_id = inspect(Case).columns.user_id
    document_case_id = inspect(Document).columns.case_id
    status = inspect(Case).columns.status

    assert telegram_id.unique is True
    assert next(iter(case_user_id.foreign_keys)).target_fullname == "users.id"
    assert next(iter(document_case_id.foreign_keys)).target_fullname == "cases.id"
    assert status.default.arg is CaseStatus.DOCUMENT_UPLOADED
    assert str(status.server_default.arg) == CaseStatus.DOCUMENT_UPLOADED.value
