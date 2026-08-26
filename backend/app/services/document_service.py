from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Case, CaseStatus, Document


BACKEND_ROOT = Path(__file__).resolve().parents[2]
STORAGE_ROOT = BACKEND_ROOT / "storage"
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}
SUPPORTED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}


def is_supported_document(filename: str | None, mime_type: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    return mime_type in SUPPORTED_MIME_TYPES or suffix in SUPPORTED_SUFFIXES


def build_storage_path(
    case_id: int,
    filename: str | None,
    mime_type: str | None,
    storage_root: Path = STORAGE_ROOT,
) -> Path:
    suffix = SUPPORTED_MIME_TYPES.get(mime_type or "")
    if suffix is None:
        candidate = Path(filename or "").suffix.lower()
        suffix = ".jpg" if candidate == ".jpeg" else candidate
    if suffix not in {".pdf", ".jpg", ".png"}:
        raise ValueError("Unsupported document type")
    return storage_root / "cases" / str(case_id) / f"{uuid4().hex}{suffix}"


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        case: Case,
        telegram_file_id: str,
        original_filename: str | None,
        mime_type: str | None,
        local_path: str,
    ) -> Document:
        document = Document(
            case_id=case.id,
            telegram_file_id=telegram_file_id,
            original_filename=original_filename,
            mime_type=mime_type,
            local_path=local_path,
        )
        case.status = CaseStatus.DOCUMENT_UPLOADED
        self.session.add(document)
        await self.session.flush()
        return document
