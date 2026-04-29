"""Runtime-facing structured models for execution artifacts and benchmarks."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionFailureCategory(str, Enum):
    """Normalized categories for execution failures."""

    NONE = "none"
    ENVIRONMENT_ISSUE = "environment_issue"
    CREDENTIAL_ISSUE = "credential_issue"
    LLM_OUTPUT_ISSUE = "llm_output_issue"
    ELEMENT_LOCATION_ISSUE = "element_location_issue"
    ASSERTION_ISSUE = "assertion_issue"
    TIMEOUT_ISSUE = "timeout_issue"
    EXECUTION_ISSUE = "execution_issue"


class FailureAnalysisResult(BaseModel):
    """Structured failure analysis for a run or a single test."""

    category: ExecutionFailureCategory = Field(default=ExecutionFailureCategory.NONE)
    summary: str = Field(default="No failure detected.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)
    suggested_action: Optional[str] = None


class RunManifest(BaseModel):
    """Stable manifest for one workflow run."""

    run_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    requirement_file: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)
    execute_ui: bool = True
    files: Dict[str, str] = Field(default_factory=dict)
    benchmark_case_id: Optional[str] = None


class BenchmarkCase(BaseModel):
    """Descriptor for an official resume/demo benchmark case."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    requirement_file: str = Field(min_length=1)
    description: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    expected_focus: List[str] = Field(default_factory=list)

