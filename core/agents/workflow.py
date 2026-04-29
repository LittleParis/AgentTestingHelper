"""Agent workflow orchestration built on top of LangGraph.

This module provides the main entry point for running the test automation workflow.
"""

from __future__ import annotations

from typing import Optional

from core.models.workflow import AgentState, ScenarioConfig
from core.agents.workflow.builder import build_workflow, create_initial_state


def run_workflow(
    requirement_text: str,
    max_iterations: int = 2,
    page_url: str = "https://example.com",
    scenario_config: Optional[ScenarioConfig] = None,
    execute_ui: bool = True,
) -> AgentState:
    """Run the end-to-end workflow."""
    initial_state = create_initial_state(
        requirement_text=requirement_text,
        max_iterations=max_iterations,
        page_url=page_url,
        scenario_config=scenario_config,
        execute_ui=execute_ui,
    )

    workflow = build_workflow()
    app = workflow.compile()

    print("=" * 60)
    print("Agent workflow started")
    print("=" * 60)

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("Agent workflow completed")
    print("=" * 60)

    return final_state


__all__ = ["run_workflow", "AgentState", "ScenarioConfig"]


if __name__ == "__main__":
    sample_requirement = """
    # User Login

    ## Description
    Users can log into the system with username and password.

    ## Acceptance Criteria
    1. Valid username and password log in successfully.
    2. Invalid password shows an error message.
    3. Unknown username shows an error message.
    4. Lock the account after 3 failed password attempts.
    """

    result = run_workflow(sample_requirement, page_url="https://example.com/login")

    print("\nFinal result:")
    print(f"- Requirements: {len(result.get('requirements') or [])}")
    print(f"- Test cases: {len(result.get('test_cases') or [])}")
    print(f"- Review passed: {result.get('review_passed')}")
    print(f"- Iterations: {result.get('iteration_count')}")
    print(f"- Script: {result.get('generated_script')}")

    execution_results = result.get("execution_results")
    if execution_results:
        print(
            f"- Execution: {execution_results['passed']}/{execution_results['total']} passed"
        )
        print(f"- Duration: {execution_results['duration']}s")
