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
