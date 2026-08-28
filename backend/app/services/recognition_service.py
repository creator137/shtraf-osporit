from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Case,
    CaseStatus,
    Document,
    DocumentRecognition,
    FineNotice,
    RecognitionStatus,
)
from app.services.extraction_service import FineNoticeExtractor, FineNoticeFields
from app.services.ocr_service import OcrProvider


class RecognitionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_pending_for_document(
        self, case: Case, document: Document
    ) -> DocumentRecognition:
        recognition = DocumentRecognition(
            document_id=document.id,
            status=RecognitionStatus.PENDING,
        )
        self.session.add(recognition)
        await self.session.flush()
        await self._upsert_notice(case.id, recognition.id, FineNoticeFields())
        return recognition

    async def save_recognized_text(
        self, case_id: int, document_id: int, raw_text: str
    ) -> DocumentRecognition:
        recognition = await self._get_or_create_recognition(document_id)
        recognition.status = RecognitionStatus.RECOGNIZED
        recognition.raw_text = raw_text
        recognition.error_message = None
        fields = FineNoticeExtractor().extract(raw_text)
        await self._upsert_notice(case_id, recognition.id, fields)
        await self._set_case_status(case_id, CaseStatus.IN_PROGRESS)
        await self.session.flush()
        return recognition

    async def process_document(
        self,
        case_id: int,
        document: Document,
        content: bytes,
        provider: OcrProvider,
    ) -> DocumentRecognition:
        recognition = await self._get_or_create_recognition(document.id)
        if recognition.status is RecognitionStatus.VERIFIED:
            raise ValueError("Verified recognition cannot be overwritten")
        recognition.status = RecognitionStatus.PROCESSING
        recognition.error_message = None
        await self._set_case_status(case_id, CaseStatus.IN_PROGRESS)
        await self.session.flush()
        try:
            result = await provider.recognize(
                content,
                document.original_filename or f"document-{document.id}",
                document.mime_type,
            )
        except Exception as exc:
            return await self.mark_failed(case_id, document.id, str(exc))
        return await self.save_recognized_text(case_id, document.id, result.text)

    async def mark_failed(
        self, case_id: int, document_id: int, error_message: str
    ) -> DocumentRecognition:
        recognition = await self._get_or_create_recognition(document_id)
        recognition.status = RecognitionStatus.FAILED
        recognition.error_message = error_message
        await self._upsert_notice(case_id, recognition.id, FineNoticeFields())
        await self._set_case_status(case_id, CaseStatus.IN_PROGRESS)
        await self.session.flush()
        return recognition

    async def update_notice(
        self, case_id: int, fields: FineNoticeFields
    ) -> FineNotice:
        notice = await self.session.scalar(
            select(FineNotice).where(FineNotice.case_id == case_id)
        )
        if notice is None:
            notice = FineNotice(case_id=case_id)
            self.session.add(notice)
        self._apply_fields(notice, fields)
        recognition = await self._latest_recognition_for_case(case_id)
        if recognition is not None:
            recognition.status = RecognitionStatus.VERIFIED
            notice.recognition_id = recognition.id
        await self._set_case_status(case_id, CaseStatus.READY)
        await self.session.flush()
        return notice

    async def _get_or_create_recognition(self, document_id: int) -> DocumentRecognition:
        recognition = await self.session.scalar(
            select(DocumentRecognition).where(DocumentRecognition.document_id == document_id)
        )
        if recognition is not None:
            return recognition
        recognition = DocumentRecognition(document_id=document_id)
        self.session.add(recognition)
        await self.session.flush()
        return recognition

    async def _latest_recognition_for_case(
        self, case_id: int
    ) -> DocumentRecognition | None:
        case = await self.session.scalar(
            select(Case)
            .where(Case.id == case_id)
            .options(selectinload(Case.documents).selectinload(Document.recognition))
        )
        if case is None:
            return None
        recognitions = [
            document.recognition
            for document in case.documents
            if document.recognition is not None
        ]
        return max(recognitions, key=lambda item: item.created_at) if recognitions else None

    async def _upsert_notice(
        self,
        case_id: int,
        recognition_id: int | None,
        fields: FineNoticeFields,
    ) -> FineNotice:
        notice = await self.session.scalar(
            select(FineNotice).where(FineNotice.case_id == case_id)
        )
        if notice is None:
            notice = FineNotice(case_id=case_id)
            self.session.add(notice)
        notice.recognition_id = recognition_id
        self._apply_fields(notice, fields)
        await self.session.flush()
        return notice

    def _apply_fields(self, notice: FineNotice, fields: FineNoticeFields) -> None:
        notice.notice_number = fields.notice_number
        notice.notice_date = fields.notice_date
        notice.uin = fields.uin
        notice.fine_amount = fields.fine_amount
        notice.article = fields.article
        notice.vehicle_plate = fields.vehicle_plate
        notice.violation_datetime = fields.violation_datetime
        notice.violation_place = fields.violation_place
        notice.issuing_authority = fields.issuing_authority

    async def _set_case_status(self, case_id: int, status: CaseStatus) -> None:
        case = await self.session.get(Case, case_id)
        if case is not None:
            case.status = status
