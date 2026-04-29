"""Structured models for requirement-level test strategy planning."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class FocusLevel(str, Enum):
    """How much attention a focus point deserves."""

    CRITICAL = "critical"
    MAJOR = "major"
    NORMAL = "normal"
    LIGHT = "light"


class ExecutionMode(str, Enum):
    """Recommended execution depth for a focus point."""

    DEEP = "deep"
    STANDARD = "standard"
    SMOKE = "smoke"


class CoverageAxis(str, Enum):
    """Supported coverage dimensions for strategy planning."""

    HAPPY_PATH = "happy_path"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    EXCEPTION = "exception"
    RECOVERY = "recovery"
    PERMISSION = "permission"
    DATA_VALIDATION = "data_validation"


class OverallRisk(str, Enum):
    """Requirement-level overall risk bucket."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FocusPointStrategy(BaseModel):
    """Strategy metadata for a single acceptance point."""

    point_id: str = Field(min_length=3, max_length=64)
    point_text: str = Field(min_length=5)
    focus_level: FocusLevel
    execution_mode: ExecutionMode
    coverage_axes: List[CoverageAxis] = Field(default_factory=list, min_length=1)
    reason: str = Field(min_length=5)
    case_weight: int = Field(ge=1, le=3)

    @field_validator("coverage_axes")
    @classmethod
    def deduplicate_axes(cls, axes: List[CoverageAxis]) -> List[CoverageAxis]:
        deduplicated: List[CoverageAxis] = []
        for axis in axes:
            if axis not in deduplicated:
                deduplicated.append(axis)
        return deduplicated or [CoverageAxis.HAPPY_PATH]


class RequirementStrategy(BaseModel):
    """Strategy output for a single requirement."""

    requirement_id: str = Field(pattern=r"^REQ_\d{1,6}$")
    focus_points: List[FocusPointStrategy] = Field(default_factory=list, min_length=1)
    overall_risk: OverallRisk
    suggested_case_budget: int = Field(ge=1, le=12)
    strategy_summary: str = Field(min_length=10)

    @model_validator(mode="after")
    def align_budget(self) -> "RequirementStrategy":
        if self.suggested_case_budget < 1:
            self.suggested_case_budget = 1
        return self


class TestStrategyPlan(BaseModel):
    """Full strategy plan for the input requirement document."""

    strategy_version: str = Field(default="v1")
    overall_summary: str = Field(min_length=10)
    requirement_strategies: List[RequirementStrategy] = Field(default_factory=list)
    total_suggested_case_budget: int = Field(ge=0)
    fallback_used: bool = Field(default=False)
    metadata: Optional[Dict[str, str]] = Field(default=None)

    @model_validator(mode="after")
    def align_total_budget(self) -> "TestStrategyPlan":
        actual_budget = sum(item.suggested_case_budget for item in self.requirement_strategies)
        if self.total_suggested_case_budget != actual_budget:
            self.total_suggested_case_budget = actual_budget
        return self

    def get_strategy_for_requirement(self, requirement_id: str) -> Optional[RequirementStrategy]:
        """Return the matching requirement strategy when present."""
        for strategy in self.requirement_strategies:
            if strategy.requirement_id == requirement_id:
                return strategy
        return None

    def to_dict(self) -> dict:
        """Backward-compatible dict export."""
        return self.model_dump()
