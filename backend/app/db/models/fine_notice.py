from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.case import Case
    from app.db.models.recognition import DocumentRecognition


class FineNotice(Base):
    __tablename__ = "fine_notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    recognition_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_recognitions.id", ondelete="SET NULL"), index=True
    )
    notice_number: Mapped[str | None] = mapped_column(String(100))
    notice_date: Mapped[str | None] = mapped_column(String(50))
    uin: Mapped[str | None] = mapped_column(String(64))
    fine_amount: Mapped[int | None] = mapped_column(Integer)
    article: Mapped[str | None] = mapped_column(String(255))
    vehicle_plate: Mapped[str | None] = mapped_column(String(32))
    violation_datetime: Mapped[str | None] = mapped_column(String(100))
    violation_place: Mapped[str | None] = mapped_column(Text)
    issuing_authority: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    case: Mapped["Case"] = relationship(back_populates="fine_notice")
    recognition: Mapped["DocumentRecognition | None"] = relationship(
        back_populates="fine_notice"
    )
