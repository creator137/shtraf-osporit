from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.fine_notice import FineNotice


class RecognitionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RECOGNIZED = "RECOGNIZED"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"


class DocumentRecognition(Base):
    __tablename__ = "document_recognitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[RecognitionStatus] = mapped_column(
        SqlEnum(RecognitionStatus, name="recognition_status"),
        default=RecognitionStatus.PENDING,
        server_default=RecognitionStatus.PENDING.value,
        nullable=False,
    )
    raw_text: Mapped[str | None] = mapped_column(Text)
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

    document: Mapped["Document"] = relationship(back_populates="recognition")
    fine_notice: Mapped["FineNotice | None"] = relationship(
        back_populates="recognition",
        passive_deletes=True,
        uselist=False,
    )
