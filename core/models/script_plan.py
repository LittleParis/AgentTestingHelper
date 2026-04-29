"""Structured models for agentic script planning."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExecutionTarget(str, Enum):
    """Preferred execution backend for a step."""

    PLAYWRIGHT_NATIVE = "playwright_native"
    MIDSCENE_AI = "midscene_ai"
    MIXED = "mixed"


class ExecutionPolicy(str, Enum):
    """Overall execution policy for a script plan."""

    NATIVE_FIRST = "native_first"
    HYBRID_BALANCED = "hybrid_balanced"
    AI_FIRST = "ai_first"


class FallbackPolicy(str, Enum):
    """Fallback behavior when planning data is incomplete."""

    DETERMINISTIC = "deterministic"
    REPAIR_WITH_RULES = "repair_with_rules"


class IntentType(str, Enum):
    """High-level intent classification for a step."""

    OPEN_PAGE = "open_page"
    INPUT = "input"
    CLICK = "click"
    WAIT = "wait"
    VERIFY = "verify"
    OBSERVE = "observe"
    GENERIC = "generic"


class NativeOperationKind(str, Enum):
    """Supported renderer-native action operations."""

    EXPECT_VISIBLE = "expect_visible"
    FILL = "fill"
    CLICK = "click"
    WAIT_LOAD = "wait_load"
    WAIT_TIMEOUT = "wait_timeout"
    NOOP = "noop"


class AssertionKind(str, Enum):
    """Supported renderer-native assertion operations."""

    LOCATOR_VISIBLE = "locator_visible"
    VALUE_EQUALS = "value_equals"
    VALUE_EMPTY = "value_empty"
    VALUE_NONEMPTY = "value_nonempty"
    PAGE_BODY_VISIBLE = "page_body_visible"
    URL_SAME = "url_same"
    URL_CHANGED = "url_changed"
    URL_MATCHES = "url_matches"
    TEXT_VISIBLE = "text_visible"


class PlannerDecisionTrace(BaseModel):
    """Small trace payload for debug and observability."""

    source: str = Field(min_length=2)
    reason: str = Field(min_length=2)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class NativeOperation(BaseModel):
    """Structured native action operation."""

    kind: NativeOperationKind
    locator: Optional[str] = None
    value: Optional[str] = None
    runtime_var: Optional[str] = None
    fallback_value: Optional[str] = None
    timeout_ms: Optional[int] = Field(default=None, ge=0)


class AssertionIntent(BaseModel):
    """Structured assertion instruction."""

    kind: AssertionKind
    locator: Optional[str] = None
    expected_value: Optional[str] = None
    runtime_var: Optional[str] = None
    regex: Optional[str] = None
    exact: bool = False


class ScenarioPlan(BaseModel):
    """Scenario-level execution metadata."""

    scenario_type: str = Field(default="generic", min_length=3)
    risk_level: str = Field(default="medium", min_length=3)
    execution_policy: ExecutionPolicy = Field(default=ExecutionPolicy.HYBRID_BALANCED)
    allow_ai_only: bool = False
    requires_runtime_credentials: bool = False
    selectors: Dict[str, str] = Field(default_factory=dict)
    safety_constraints: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ScriptSetupPlan(BaseModel):
    """Setup instructions shared by all steps in a script."""

    page_url: str = Field(min_length=1)
    wait_for: str = Field(default="domcontentloaded")
    initial_wait_ms: int = Field(default=1500, ge=0)
    required_env_vars: List[str] = Field(default_factory=list)
    runtime_variables: Dict[str, str] = Field(
        default_factory=lambda: {
            "username": "runtimeUsername",
            "password": "runtimePassword",
        }
    )
    mask_locator_aliases: List[str] = Field(default_factory=list)
    safety_constraints: List[str] = Field(default_factory=list)


class ScriptStepPlan(BaseModel):
    """Structured plan for one generated script step."""

    step_number: int = Field(ge=1)
    original_action: str = Field(default="", min_length=0)
    original_expected: str = Field(default="", min_length=0)
    normalized_data: str = Field(default="", min_length=0)
    intent_type: IntentType = Field(default=IntentType.GENERIC)
    target: str = Field(default="")
    preferred_executor: ExecutionTarget = Field(default=ExecutionTarget.MIXED)
    action_prompt: str = Field(default="")
    verify_prompt: str = Field(default="")
    native_operations: List[NativeOperation] = Field(default_factory=list)
    assertion_intents: List[AssertionIntent] = Field(default_factory=list)
    decision_trace: Optional[PlannerDecisionTrace] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScriptExecutionPlan(BaseModel):
    """Structured script execution plan for one test case."""

    testcase_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    requirement_id: Optional[str] = None
    scenario: ScenarioPlan
    setup: ScriptSetupPlan
    steps: List[ScriptStepPlan] = Field(default_factory=list)
    final_assertions: List[AssertionIntent] = Field(default_factory=list)
    fallback_policy: FallbackPolicy = Field(default=FallbackPolicy.DETERMINISTIC)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("steps")
    @classmethod
    def ensure_monotonic_steps(cls, steps: List[ScriptStepPlan]) -> List[ScriptStepPlan]:
        normalized: List[ScriptStepPlan] = []
        for index, step in enumerate(steps, start=1):
            if step.step_number != index:
                step = step.model_copy(update={"step_number": index})
            normalized.append(step)
        return normalized
