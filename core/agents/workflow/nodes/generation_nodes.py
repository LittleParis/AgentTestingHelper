"""Test case generation nodes."""

from langgraph.types import Overwrite, Send

from core.agents.test_case_generator import TestCaseGenerator
from core.agents.workflow.scenarios import (
    is_login_only_scenario,
    build_login_only_test_case,
)
from core.agents.workflow.utils import get_improvement_hints
from core.models.workflow import AgentState, SingleRequirementGenerationState


def generate_test_cases_node(state: AgentState) -> dict:
    """Prepare parallel test-case generation."""
    print("\n[Agent] Dispatching parallel test-case generation...")

    requirements = state.get("requirements") or []
    improvement_hints = get_improvement_hints(state)

    if improvement_hints:
        print(
            "  [INFO] Iteration "
            f"{state.get('iteration_count', 0) + 1}: injecting {len(improvement_hints)} review hints."
        )

    return {
        "test_cases": Overwrite([]),
        "current_step": "test_case_generation_dispatched",
        "agent_messages": [
            {
                "role": "generator",
                "content": f"Dispatching {len(requirements)} requirements for parallel generation.",
            }
        ],
    }


def fan_out_requirements(state: AgentState):
    """Fan out test-case generation work across requirements."""
    requirements = state.get("requirements") or []
    if not requirements:
        return "finalize_test_case_generation"

    improvement_hints = get_improvement_hints(state)
    iteration_count = state.get("iteration_count", 0)

    return [
        Send(
            "generate_test_case_for_requirement",
            {
                "requirement": requirement,
                "strategy_context": requirement.get("generation_context"),
                "improvement_hints": improvement_hints,
                "iteration_count": iteration_count,
            },
        )
        for requirement in requirements
    ]


def generate_test_case_for_requirement_node(
    state: SingleRequirementGenerationState,
) -> dict:
    """Generate test cases for a single requirement."""
    requirement = dict(state["requirement"])
    if state.get("strategy_context") and not requirement.get("generation_context"):
        requirement["generation_context"] = state.get("strategy_context")
    requirement_id = requirement.get("id", "UNKNOWN_REQ")

    if is_login_only_scenario({"scenario_type": requirement.get("scenario_type")}):
        bounded_test_case = build_login_only_test_case(requirement)
        print(f"  [OK] {requirement_id}: using deterministic login-only test case.")
        return {
            "test_cases": [bounded_test_case],
            "agent_messages": [
                {
                    "role": "generator",
                    "content": f"{requirement_id}: generated 1 bounded login-only test case.",
                }
            ],
        }

    generator = TestCaseGenerator()

    try:
        test_cases = generator.generate(
            requirement,
            improvement_hints=state.get("improvement_hints"),
        )
        print(f"  [OK] {requirement_id}: generated {len(test_cases)} test cases.")
        return {
            "test_cases": test_cases,
            "agent_messages": [
                {
                    "role": "generator",
                    "content": f"{requirement_id}: generated {len(test_cases)} test cases.",
                }
            ],
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"  [FAIL] {requirement_id}: {exc}")
        return {
            "agent_messages": [
                {
                    "role": "generator",
                    "content": f"{requirement_id}: generation failed with {exc}",
                }
            ],
        }


def finalize_test_case_generation_node(state: AgentState) -> dict:
    """Mark the parallel generation step as complete."""
    test_cases = state.get("test_cases") or []
    requirements = state.get("requirements") or []

    print(
        "\n[Agent] Parallel generation complete: "
        f"{len(requirements)} requirements, {len(test_cases)} test cases."
    )

    return {
        "current_step": "test_cases_generated",
        "agent_messages": [
            {
                "role": "generator",
                "content": (
                    f"Parallel generation complete: {len(requirements)} requirements, "
                    f"{len(test_cases)} test cases."
                ),
            }
        ],
    }


def optimize_test_cases_node(state: AgentState) -> dict:
    """Keep a small compatibility optimization hook."""
    optimized = []
    for test_case in state.get("test_cases", []):
        if "priority" not in test_case:
            test_case["priority"] = "medium"
        optimized.append(test_case)
    return {"test_cases": optimized}