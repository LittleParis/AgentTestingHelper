"""Workflow state models for LangGraph orchestration."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.types import Overwrite


def merge_lists(left: Optional[List[dict]], right: Optional[List[dict]]) -> List[dict]:
    """Reducer used by LangGraph when multiple parallel nodes update the same list field."""
    return [*(left or []), *(right or [])]


class AgentState(TypedDict, total=False):
    """Shared workflow state."""

    requirement_text: str
    requirements: Optional[List[dict]]
    planned_requirements: Optional[List[dict]]
    test_strategy: Optional[dict]
    requirement_summary: Optional[str]
    test_cases: Annotated[List[dict], merge_lists]

    review_passed: Optional[bool]
    review_score: Optional[float]
    review_comments: Optional[List[dict]]
    review_suggestions: Optional[List[str]]

    iteration_count: int
    max_iterations: int
    feedback: Optional[List[str]]

    generated_script: Optional[str]
    script_plans: Optional[List[dict]]
    page_url: Optional[str]
    scenario_config: Optional[dict]
    execution_results: Optional[dict]
    allure_report_path: Optional[str]

    current_step: str
    agent_messages: Annotated[List[dict], merge_lists]


class SingleRequirementGenerationState(TypedDict):
    """Input schema for a single parallel test-case generation task."""

    requirement: dict
    strategy_context: Optional[dict]
    improvement_hints: Optional[List[str]]
    iteration_count: int


class ScenarioConfig(TypedDict, total=False):
    """Optional runtime constraints for a workflow execution."""

    scenario_type: str
    page_url: str
    credentials: Dict[str, Any]
    success_signal: Dict[str, Any]
    manual_wait: bool
    mfa_mode: str
    allowed_actions: List[str]
    forbidden_actions: List[str]
    manual_wait_timeout_ms: int