from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.case import Case


class LegalAnalysisStatus(str, Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    DOCUMENTS_GENERATED = "DOCUMENTS_GENERATED"
    FAILED = "FAILED"


class LegalGroundStatus(str, Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class GeneratedDocumentType(str, Enum):
    COMPLAINT = "COMPLAINT"
    EVIDENCE_PETITION = "EVIDENCE_PETITION"


class GeneratedDocumentFormat(str, Enum):
    DOCX = "DOCX"
    PDF = "PDF"


class LegalAnalysis(Base):
    __tablename__ = "legal_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[LegalAnalysisStatus] = mapped_column(
        SqlEnum(LegalAnalysisStatus, name="legal_analysis_status"),
        default=LegalAnalysisStatus.PENDING_CONFIRMATION,
        server_default=LegalAnalysisStatus.PENDING_CONFIRMATION.value,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    result: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    grounds: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    missing_evidence: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    case: Mapped["Case"] = relationship(back_populates="legal_analysis")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    legal_analysis_id: Mapped[int | None] = mapped_column(
        ForeignKey("legal_analyses.id", ondelete="SET NULL"), index=True
    )
    document_type: Mapped[GeneratedDocumentType] = mapped_column(
        SqlEnum(GeneratedDocumentType, name="generated_document_type"),
        nullable=False,
    )
    file_format: Mapped[GeneratedDocumentFormat] = mapped_column(
        SqlEnum(GeneratedDocumentFormat, name="generated_document_format"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped["Case"] = relationship(back_populates="generated_documents")
