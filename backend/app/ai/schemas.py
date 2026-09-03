from typing import Literal

from pydantic import BaseModel, Field


class LegalGround(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    supporting_fact_ids: list[str] = Field(default_factory=list)
    legal_rule_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    recommended: bool = False


class LegalAnalysisResult(BaseModel):
    summary: str = Field(min_length=1)
    grounds: list[LegalGround] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    additional_questions: list[str] = Field(default_factory=list, max_length=5)
    overall_assessment: str = Field(min_length=1)


class GeneratedLegalDocument(BaseModel):
    title: str = Field(min_length=1)
    sections: list[str] = Field(min_length=1)


class DocumentClaimEvidenceCheck(BaseModel):
    claim: str = Field(min_length=1)
    confirmed_by: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    request_needed: list[str] = Field(default_factory=list)
    result: Literal[
        "Доказательств достаточно",
        "Требуются дополнительные материалы",
        "Основание подтверждено только словами пользователя",
    ]


class DocumentEvidenceReview(BaseModel):
    claims: list[DocumentClaimEvidenceCheck] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    request_needed: list[str] = Field(default_factory=list)
    overall_result: Literal[
        "Доказательств достаточно",
        "Требуются дополнительные материалы",
        "Основание подтверждено только словами пользователя",
    ]
    sufficiency_level: str = Field(pattern="^(HIGH|PARTIAL|INSUFFICIENT)$")
    summary: str = Field(min_length=1)
