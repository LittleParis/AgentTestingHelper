"""Structured review result models."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class CommentSeverity(str, Enum):
    """Severity for a review comment."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CommentType(str, Enum):
    """Type for a review comment."""

    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NO_COVERAGE = "no_coverage"
    PARSE_ERROR = "parse_error"
    EXECUTABILITY = "executability"


class ReviewComment(BaseModel):
    """A single review comment."""

    type: CommentType
    severity: CommentSeverity = CommentSeverity.MEDIUM
    message: str = Field(min_length=5)
    field: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return value.strip()


class ReviewDimensions(BaseModel):
    """Dimension scores for the main quality review."""

    completeness: int = Field(ge=0, le=20)
    coverage: int = Field(ge=0, le=20)
    reasonability: int = Field(ge=0, le=20)
    independence: int = Field(ge=0, le=20)
    clarity: int = Field(ge=0, le=20)

    def total(self) -> int:
        return self.completeness + self.coverage + self.reasonability + self.independence + self.clarity

    def to_dict(self) -> dict:
        return {
            "completeness": self.completeness,
            "coverage": self.coverage,
            "reasonability": self.reasonability,
            "independence": self.independence,
            "clarity": self.clarity,
        }


class ReviewResult(BaseModel):
    """Review result for one requirement's generated test cases."""

    passed: bool
    score: int = Field(ge=0, le=100)
    dimensions: Optional[ReviewDimensions] = None
    comments: List[ReviewComment] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    executability_score: Optional[int] = Field(default=None, ge=0, le=20)
    executability_findings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_score_consistency(self) -> "ReviewResult":
        if self.dimensions:
            self.score = self.dimensions.total()
        return self

    @field_validator("suggestions")
    @classmethod
    def validate_suggestions(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(item.strip() for item in value if item and item.strip()))

    @field_validator("executability_findings")
    @classmethod
    def validate_executability_findings(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(item.strip() for item in value if item and item.strip()))

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "comments": [comment.model_dump() for comment in self.comments],
            "suggestions": self.suggestions,
            "executability_score": self.executability_score,
            "executability_findings": self.executability_findings,
        }


class RequirementReviewDetail(BaseModel):
    """Review details for one requirement."""

    requirement_id: str
    requirement_title: str
    passed: bool
    score: float = Field(ge=0, le=100)
    dimensions: Optional[ReviewDimensions] = None
    comments: List[ReviewComment] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    executability_score: Optional[int] = Field(default=None, ge=0, le=20)
    executability_findings: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "requirement_title": self.requirement_title,
            "passed": self.passed,
            "score": self.score,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "comments": [comment.model_dump() for comment in self.comments],
            "suggestions": self.suggestions,
            "executability_score": self.executability_score,
            "executability_findings": self.executability_findings,
        }


class ReviewAllResult(BaseModel):
    """Aggregated review result across requirements."""

    passed: bool
    total_score: float = Field(ge=0, le=100)
    details: List[RequirementReviewDetail] = Field(default_factory=list)
    summary: str = Field(min_length=5)

    @model_validator(mode="after")
    def validate_passed_consistency(self) -> "ReviewAllResult":
        if self.details:
            self.passed = all(detail.passed for detail in self.details) and self.total_score >= 60
        return self

    @field_validator("total_score")
    @classmethod
    def validate_total_score(cls, value: float) -> float:
        return round(value, 1)

    def get_passed_count(self) -> int:
        return sum(1 for detail in self.details if detail.passed)

    def get_failed_details(self) -> List[RequirementReviewDetail]:
        return [detail for detail in self.details if not detail.passed]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "total_score": self.total_score,
            "details": [detail.to_dict() for detail in self.details],
            "summary": self.summary,
        }

