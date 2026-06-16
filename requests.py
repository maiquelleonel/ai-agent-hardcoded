# Arquivo para centralizar classes de Request

from pydantic import BaseModel, Field


class InitiativeRequest(BaseModel):
    initiative: str


class AssessmentComparisonRequest(BaseModel):
    current_id: str
    previous_id: str


class HumanReviewActionRequest(BaseModel):
    reviewer_name: str
    action: str = Field(description="in_review, approved ou rejected")
    resolution_note: str = ""


class AssessRequest(BaseModel):
    initiative: str


class CompareRequest(BaseModel):
    current_id: str
    previous_id: str
