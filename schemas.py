from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AssessmentScores(BaseModel):
    business_value: int = Field(ge=0, le=10)
    technical_feasibility: int = Field(ge=0, le=10)
    data_readiness: int = Field(ge=0, le=10)
    governance_risk: int = Field(ge=0, le=10)
    integration_effort: int = Field(ge=0, le=10)
    time_to_value: int = Field(ge=0, le=10)
    overall_viability: int = Field(ge=0, le=10)


class WorkflowState(BaseModel):
    received: bool = False
    parsed: bool = False
    classified: bool = False
    risks_enriched: bool = False
    stack_enriched: bool = False
    scored: bool = False
    rules_applied: bool = False
    review_decided: bool = False
    completed: bool = False


class ScoreExplanation(BaseModel):
    dimension: str
    original_score: int
    adjusted_score: int
    reason: str


class ReviewDecision(BaseModel):
    requires_human_review: bool = False
    confidence_level: str = Field(description="high, medium ou low")
    review_reason: str = ""


class SimilarCase(BaseModel):
    assessment_id: str
    created_at: datetime
    initiative_excerpt: str
    viability_score: int
    similarity_score: int = Field(ge=0, le=100)
    review_status: Optional[str] = None
    review_reason: Optional[str] = None


class MemoryContext(BaseModel):
    similar_cases: List[SimilarCase] = Field(default_factory=list)
    memory_summary: str = ""


class InitiativeAssessment(BaseModel):
    business_problem: str = Field(description="Problema de negócio principal")
    potential_value: str = Field(description="Valor potencial para a organização")
    technical_complexity: str = Field(description="Avaliação da complexidade técnica com justificativa breve")
    main_risks: List[str] = Field(description="Principais riscos da iniciativa")
    initial_stack: List[str] = Field(description="Stack inicial recomendada")
    quick_wins: List[str] = Field(description="Quick wins de curto prazo")
    viability_score: int = Field(description="Nota final de viabilidade de 0 a 10")
    scores: Optional[AssessmentScores] = None
    workflow_state: Optional[WorkflowState] = None
    score_explanations: List[ScoreExplanation] = Field(default_factory=list)
    review_decision: Optional[ReviewDecision] = None
    memory_context: Optional[MemoryContext] = None


class ParsedInitiative(BaseModel):
    initiative_name: str = Field(description="Nome resumido da iniciativa")
    business_area: str = Field(description="Área de negócio principal")
    business_problem: str = Field(description="Problema de negócio a ser resolvido")
    target_users: List[str] = Field(description="Usuários ou áreas impactadas")
    initiative_type: str = Field(description="Tipo principal da iniciativa")
    expected_value: str = Field(description="Valor esperado para a organização")
    required_data: List[str] = Field(description="Dados necessários ou presumidos")
    integrations: List[str] = Field(description="Integrações necessárias ou presumidas")
    constraints: List[str] = Field(description="Restrições, premissas ou dependências")
    regulatory_risks: List[str] = Field(description="Riscos regulatórios ou de governança")
    summary: str = Field(description="Resumo executivo da iniciativa")


class SavedAssessment(BaseModel):
    id: str
    created_at: datetime
    initiative: str
    result: InitiativeAssessment


class AssessmentComparisonResult(BaseModel):
    summary: str
    major_differences: List[str]
    recommendation: str


class HumanReviewItem(BaseModel):
    review_id: str
    assessment_id: str
    created_at: datetime
    priority: str = Field(description="high, medium ou low")
    status: str = Field(description="new, in_review, approved, rejected")
    review_reason: str
    confidence_level: str
    assigned_to: Optional[str] = None
    resolution_note: str = ""
    resolved_at: Optional[datetime] = None
