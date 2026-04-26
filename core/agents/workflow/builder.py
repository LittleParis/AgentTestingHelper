"""Workflow graph builder."""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, StateGraph

from core.models.workflow import AgentState, ScenarioConfig, SingleRequirementGenerationState
from core.agents.workflow.nodes import (
    analyze_requirements_node,
    plan_test_strategy_node,
    plan_case_budgets_node,
    generate_test_cases_node,
    generate_test_case_for_requirement_node,
    finalize_test_case_generation_node,
    review_test_cases_node,
    increment_iteration,
    plan_script_generation_node,
    generate_script_node,
    execute_tests_node,
    generate_report_node,
)
from core.agents.workflow.routing import should_regenerate
from core.agents.workflow.nodes.generation_nodes import fan_out_requirements


def build_workflow() -> StateGraph:
    """Build the full LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze_requirements", analyze_requirements_node)
    workflow.add_node("plan_test_strategy", plan_test_strategy_node)
    workflow.add_node("plan_case_budgets", plan_case_budgets_node)
    workflow.add_node("generate_test_cases", generate_test_cases_node)
    workflow.add_node(
        "generate_test_case_for_requirement",
        generate_test_case_for_requirement_node,
        input_schema=SingleRequirementGenerationState,
    )
    workflow.add_node("finalize_test_case_generation", finalize_test_case_generation_node)
    workflow.add_node("review_test_cases", review_test_cases_node)
    workflow.add_node("increment_iteration", increment_iteration)
    workflow.add_node("plan_script_generation", plan_script_generation_node)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("execute_tests", execute_tests_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.set_entry_point("analyze_requirements")

    workflow.add_edge("analyze_requirements", "plan_test_strategy")
    workflow.add_edge("plan_test_strategy", "plan_case_budgets")
    workflow.add_edge("plan_case_budgets", "generate_test_cases")
    workflow.add_conditional_edges("generate_test_cases", fan_out_requirements)
    workflow.add_edge("generate_test_case_for_requirement", "finalize_test_case_generation")
    workflow.add_edge("finalize_test_case_generation", "review_test_cases")

    workflow.add_conditional_edges(
        "review_test_cases",
        should_regenerate,
        {
            "regenerate": "increment_iteration",
            "end": "plan_script_generation",
        },
    )

    workflow.add_edge("increment_iteration", "generate_test_cases")
    workflow.add_edge("plan_script_generation", "generate_script")
    workflow.add_edge("generate_script", "execute_tests")
    workflow.add_edge("execute_tests", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow


def create_initial_state(
    requirement_text: str,
    max_iterations: int = 2,
    page_url: str = "https://example.com",
    scenario_config: Optional[ScenarioConfig] = None,
) -> AgentState:
    """Create the initial workflow state."""
    resolved_page_url = page_url
    if scenario_config and scenario_config.get("page_url"):
        resolved_page_url = str(scenario_config["page_url"])

    return {
        "requirement_text": requirement_text,
        "requirements": None,
        "planned_requirements": None,
        "test_strategy": None,
        "requirement_summary": None,
        "test_cases": [],
        "review_passed": None,
        "review_score": None,
        "review_comments": None,
        "review_suggestions": None,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "feedback": [],
        "generated_script": None,
        "script_plans": None,
        "page_url": resolved_page_url,
        "scenario_config": scenario_config,
        "execution_results": None,
        "allure_report_path": None,
        "current_step": "init",
        "agent_messages": [],
    }