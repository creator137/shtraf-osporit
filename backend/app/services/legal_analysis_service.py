import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.deepseek_client import DeepSeekClient
from app.ai.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    ANALYSIS_USER_TEMPLATE,
    DOCUMENT_SYSTEM_PROMPT,
    DOCUMENT_USER_TEMPLATE,
)
from app.ai.schemas import GeneratedLegalDocument, LegalAnalysisResult
from app.config import get_settings
from app.db.models import (
    Case,
    Document,
    GeneratedDocument,
    GeneratedDocumentType,
    LegalAnalysis,
    LegalAnalysisStatus,
    LegalAssessment,
    LegalAssessmentStatus,
    LegalGroundStatus,
)
from app.services.generated_document_service import GeneratedDocumentService
from app.services.legal_rules import LEGAL_SOURCES, RULES, answer_label, serialize_rule


class LegalAnalysisService:
    def __init__(self, session: AsyncSession, client: DeepSeekClient | None = None) -> None:
        self.session = session
        self.client = client or DeepSeekClient(get_settings())

    async def get_for_case(self, case_id: int) -> LegalAnalysis | None:
        return await self.session.scalar(
            select(LegalAnalysis).where(LegalAnalysis.case_id == case_id)
        )

    async def analyze_case(self, case_id: int) -> LegalAnalysis:
        case = await self._load_case(case_id)
        if case is None:
            raise ValueError("Case not found")
        if (
            case.legal_assessment is None
            or case.legal_assessment.status is not LegalAssessmentStatus.COMPLETED
        ):
            raise ValueError("Legal questionnaire must be completed")

        context = build_analysis_context(case, case.legal_assessment)
        user_prompt = ANALYSIS_USER_TEMPLATE.format(
            context_json=json.dumps(context, ensure_ascii=False, indent=2)
        )
        result = await self.client.complete_json(
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=LegalAnalysisResult,
        )
        assert isinstance(result, LegalAnalysisResult)
        sanitized = sanitize_analysis_result(result, context)

        analysis = await self.get_for_case(case.id)
        settings = get_settings()
        if analysis is None:
            analysis = LegalAnalysis(
                case_id=case.id,
                provider="deepseek",
                model=settings.deepseek_model,
            )
            self.session.add(analysis)
        analysis.status = LegalAnalysisStatus.PENDING_CONFIRMATION
        analysis.provider = "deepseek"
        analysis.model = settings.deepseek_model
        analysis.input_summary = context
        analysis.result = sanitized.model_dump()
        analysis.grounds = [
            {**ground.model_dump(), "status": LegalGroundStatus.PROPOSED.value}
            for ground in sanitized.grounds
        ]
        analysis.missing_evidence = sanitized.missing_evidence
        analysis.error_message = None
        await self.session.flush()
        return analysis

    async def set_ground_status(
        self, case_id: int, ground_id: str, status: LegalGroundStatus
    ) -> LegalAnalysis:
        analysis = await self.get_for_case(case_id)
        if analysis is None:
            raise ValueError("Legal analysis not found")
        changed = False
        grounds = []
        for ground in analysis.grounds:
            next_ground = dict(ground)
            if next_ground.get("id") == ground_id:
                next_ground["status"] = status.value
                changed = True
            grounds.append(next_ground)
        if not changed:
            raise ValueError("Legal ground not found")
        analysis.grounds = grounds
        if any(item.get("status") == LegalGroundStatus.CONFIRMED.value for item in grounds):
            analysis.status = LegalAnalysisStatus.CONFIRMED
        else:
            analysis.status = LegalAnalysisStatus.PENDING_CONFIRMATION
        await self.session.flush()
        return analysis

    async def generate_documents(self, case_id: int) -> list[GeneratedDocument]:
        case = await self._load_case(case_id)
        analysis = await self.get_for_case(case_id)
        if case is None or analysis is None:
            raise ValueError("Legal analysis not found")
        confirmed = [
            ground for ground in analysis.grounds
            if ground.get("status") == LegalGroundStatus.CONFIRMED.value
        ]
        if not confirmed:
            raise ValueError("No confirmed legal grounds")

        context = {
            "case": analysis.input_summary.get("case", {}),
            "facts": analysis.input_summary.get("facts", {}),
            "questionnaire": analysis.input_summary.get("questionnaire", {}),
            "confirmed_grounds": confirmed,
            "missing_evidence": analysis.missing_evidence,
            "legal_rules": analysis.input_summary.get("legal_rules", []),
            "legal_sources": analysis.input_summary.get("legal_sources", []),
        }
        documents: list[GeneratedDocument] = []
        complaint = await self._generate_document(context, "жалобу на постановление")
        documents.extend(
            await GeneratedDocumentService(self.session).save_pair(
                case=case,
                analysis=analysis,
                document_type=GeneratedDocumentType.COMPLAINT,
                title=complaint.title,
                sections=complaint.sections,
            )
        )
        if analysis.missing_evidence:
            petition = await self._generate_document(
                context,
                "ходатайство об истребовании доказательств",
            )
            documents.extend(
                await GeneratedDocumentService(self.session).save_pair(
                    case=case,
                    analysis=analysis,
                    document_type=GeneratedDocumentType.EVIDENCE_PETITION,
                    title=petition.title,
                    sections=petition.sections,
                )
            )
        analysis.status = LegalAnalysisStatus.DOCUMENTS_GENERATED
        await self.session.flush()
        return documents

    async def _generate_document(
        self, context: dict[str, Any], document_kind: str
    ) -> GeneratedLegalDocument:
        user_prompt = DOCUMENT_USER_TEMPLATE.format(
            document_kind=document_kind,
            context_json=json.dumps(context, ensure_ascii=False, indent=2),
        )
        result = await self.client.complete_json(
            system_prompt=DOCUMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=GeneratedLegalDocument,
        )
        assert isinstance(result, GeneratedLegalDocument)
        return result

    async def _load_case(self, case_id: int) -> Case | None:
        return await self.session.scalar(
            select(Case)
            .where(Case.id == case_id)
            .options(
                selectinload(Case.user),
                selectinload(Case.documents).selectinload(Document.recognition),
                selectinload(Case.fine_notice),
                selectinload(Case.legal_assessment),
                selectinload(Case.legal_analysis),
            )
        )


def build_analysis_context(case: Case, assessment: LegalAssessment) -> dict[str, Any]:
    notice = case.fine_notice
    correspondence_address = (assessment.answers.get("correspondence_address") or "").strip()
    facts = {
        "notice_number": notice.notice_number if notice else None,
        "notice_date": notice.notice_date if notice else None,
        "violation_datetime": notice.violation_datetime if notice else None,
        "article": notice.article if notice else None,
        "vehicle_plate": notice.vehicle_plate if notice else None,
        "violation_place": notice.violation_place if notice else None,
        "issuing_authority": notice.issuing_authority if notice else None,
        "fine_amount": notice.fine_amount if notice else None,
        "correspondence_address": correspondence_address or None,
    }
    answer_facts = {
        f"answer_{question_id}": answer_label(question_id, value)
        for question_id, value in assessment.answers.items()
    }
    rule_results = assessment.results
    missing_evidence = sorted(
        {
            str(item.get("name"))
            for result in rule_results
            for item in result.get("evidence_items", [])
            if item.get("status") in {"NEEDED", "VERIFY"} and item.get("name")
        }
    )
    return {
        "case": {"id": case.id, "facts": facts},
        "facts": {
            **{key: value for key, value in facts.items() if value not in {None, ""}},
            **answer_facts,
        },
        "questionnaire": {
            "answers": answer_facts,
            "completed_at": assessment.completed_at.isoformat()
            if assessment.completed_at
            else None,
            "rules_version": assessment.rules_version,
        },
        "rule_results": rule_results,
        "legal_rules": [serialize_rule(rule) for rule in RULES],
        "legal_sources": list(LEGAL_SOURCES),
        "missing_evidence": missing_evidence,
        "unknown_facts": [
            key for key, value in facts.items() if value in {None, ""}
        ],
    }


def sanitize_analysis_result(
    result: LegalAnalysisResult, context: dict[str, Any]
) -> LegalAnalysisResult:
    rule_ids = {rule["code"] for rule in context["legal_rules"]}
    source_ids = {source["id"] for source in context["legal_sources"]}
    fact_ids = set(context["facts"])
    grounds = []
    for ground in result.grounds:
        clean_rules = [item for item in ground.legal_rule_ids if item in rule_ids]
        clean_sources = [item for item in ground.source_ids if item in source_ids]
        clean_facts = [item for item in ground.supporting_fact_ids if item in fact_ids]
        if not clean_rules or not clean_sources or not clean_facts:
            continue
        grounds.append(
            ground.model_copy(
                update={
                    "legal_rule_ids": clean_rules,
                    "source_ids": clean_sources,
                    "supporting_fact_ids": clean_facts,
                }
            )
        )
    missing = sorted(
        {
            *result.missing_evidence,
            *[
                item
                for ground in grounds
                for item in ground.missing_evidence
            ],
        }
    )
    return LegalAnalysisResult(
        summary=result.summary,
        grounds=grounds,
        missing_evidence=missing,
        additional_questions=result.additional_questions[:5],
        overall_assessment=result.overall_assessment,
    )
