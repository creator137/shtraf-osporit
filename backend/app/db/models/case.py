from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.user import User


class CaseStatus(str, Enum):
    NEW = "NEW"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[CaseStatus] = mapped_column(
        SqlEnum(CaseStatus, name="case_status"),
        default=CaseStatus.NEW,
        server_default=CaseStatus.NEW.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="cases")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", passive_deletes=True
    )
