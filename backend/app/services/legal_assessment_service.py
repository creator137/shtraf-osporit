from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LegalAssessment, LegalAssessmentStatus
from app.services.legal_rules import (
    RULES_VERSION,
    LegalQuestion,
    evaluate_rules,
    get_next_question,
    get_question,
)


class LegalAssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_case(self, case_id: int) -> LegalAssessment | None:
        return await self.session.scalar(
            select(LegalAssessment).where(LegalAssessment.case_id == case_id)
        )

    async def start(self, case_id: int, *, restart: bool = False) -> LegalAssessment:
        assessment = await self.get_for_case(case_id)
        if assessment is None:
            assessment = LegalAssessment(case_id=case_id, rules_version=RULES_VERSION)
            self.session.add(assessment)
        elif restart:
            assessment.status = LegalAssessmentStatus.IN_PROGRESS
            assessment.answers = {}
            assessment.results = []
            assessment.rules_version = RULES_VERSION
            assessment.completed_at = None
        await self.session.flush()
        return assessment

    async def answer(
        self,
        assessment: LegalAssessment,
        question_id: str,
        value: str,
        notice_article: str | None = None,
    ) -> LegalQuestion | None:
        if assessment.status is LegalAssessmentStatus.COMPLETED:
            raise ValueError("Assessment is already completed")

        current_question = get_next_question(assessment.answers, notice_article)
        if current_question is None or current_question.id != question_id:
            raise ValueError("Answer does not match the current question")
        question = get_question(question_id)
        if question is None or value not in {option.value for option in question.options}:
            raise ValueError("Unknown answer")

        assessment.answers = {**assessment.answers, question_id: value}
        next_question = get_next_question(assessment.answers, notice_article)
        if next_question is None:
            assessment.results = evaluate_rules(assessment.answers, notice_article)
            assessment.status = LegalAssessmentStatus.COMPLETED
            assessment.completed_at = datetime.now(UTC)
        await self.session.flush()
        return next_question
