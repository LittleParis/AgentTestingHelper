"""Agent workflow orchestration built on top of LangGraph."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Overwrite, Send

from core.agents.case_reviewer import CaseReviewer
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.agents.test_case_generator import TestCaseGenerator
from core.automation.allure_reporter import AllureReporter
from core.automation.midscene_generator import MidsceneScriptGenerator
from core.automation.test_executor import TestExecutor
from core.utils.project_paths import GENERATED_TESTS_DIR


def _merge_lists(left: Optional[List[dict]], right: Optional[List[dict]]) -> List[dict]:
    """Reducer used by LangGraph when multiple parallel nodes update the same list field."""
    return [*(left or []), *(right or [])]


class AgentState(TypedDict, total=False):
    """Shared workflow state."""

    requirement_text: str
    requirements: Optional[List[dict]]
    requirement_summary: Optional[str]
    test_cases: Annotated[List[dict], _merge_lists]

    review_passed: Optional[bool]
    review_score: Optional[float]
    review_comments: Optional[List[dict]]
    review_suggestions: Optional[List[str]]

    iteration_count: int
    max_iterations: int
    feedback: Optional[List[str]]

    generated_script: Optional[str]
    page_url: Optional[str]
    scenario_config: Optional[dict]
    execution_results: Optional[dict]
    allure_report_path: Optional[str]

    current_step: str
    agent_messages: Annotated[List[dict], _merge_lists]


class SingleRequirementGenerationState(TypedDict):
    """Input schema for a single parallel test-case generation task."""

    requirement: dict
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


def _get_improvement_hints(state: AgentState) -> Optional[List[str]]:
    """Limit review feedback before passing it back into the generator."""
    iteration = state.get("iteration_count", 0)
    review_suggestions = state.get("review_suggestions") or []

    if iteration <= 0 or not review_suggestions:
        return None

    max_hints = 5
    return review_suggestions[:max_hints]


def analyze_requirements_node(state: AgentState) -> dict:
    """Analyze the requirement document."""
    print("\n[Agent] Analyzing requirements...")

    analyzer = RequirementAnalyzer()
    result = analyzer.analyze(state["requirement_text"])
    requirements = result.get("requirements", [])

    return {
        "requirements": requirements,
        "requirement_summary": result.get("summary", ""),
        "current_step": "requirement_analyzed",
        "agent_messages": [
            {
                "role": "analyzer",
                "content": f"Identified {len(requirements)} requirements.",
            }
        ],
    }


def generate_test_cases_node(state: AgentState) -> dict:
    """Prepare parallel test-case generation."""
    print("\n[Agent] Dispatching parallel test-case generation...")

    requirements = state.get("requirements") or []
    improvement_hints = _get_improvement_hints(state)

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

    improvement_hints = _get_improvement_hints(state)
    iteration_count = state.get("iteration_count", 0)

    return [
        Send(
            "generate_test_case_for_requirement",
            {
                "requirement": requirement,
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
    requirement = state["requirement"]
    requirement_id = requirement.get("id", "UNKNOWN_REQ")
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


def review_test_cases_node(state: AgentState) -> dict:
    """Review generated test cases."""
    print("\n[Agent] Reviewing generated test cases...")

    requirements = state.get("requirements") or []
    test_cases = state.get("test_cases") or []

    try:
        reviewer = CaseReviewer()
        result = reviewer.review_all(requirements, test_cases)

        passed = result.get("passed", False)
        score = result.get("total_score", 0)
        details = result.get("details", [])

        all_comments: List[dict] = []
        all_suggestions: List[str] = []

        for detail in details:
            requirement_id = detail.get("requirement_id", "")
            for comment in detail.get("comments", []):
                comment["requirement_id"] = requirement_id
                all_comments.append(comment)
            for suggestion in detail.get("suggestions", []):
                all_suggestions.append(f"[{requirement_id}] {suggestion}")

        if passed:
            print(f"  [OK] Review passed with score {score}.")
        else:
            print(f"  [WARN] Review failed with score {score}.")
            print(f"  Found {len(all_comments)} issues.")

        return {
            "review_passed": passed,
            "review_score": score,
            "review_comments": all_comments,
            "review_suggestions": all_suggestions,
            "current_step": "reviewed",
            "agent_messages": [
                {
                    "role": "reviewer",
                    "content": f"Review {'passed' if passed else 'failed'} with score {score}/100.",
                }
            ],
        }

    except Exception as exc:
        print(f"  [ERROR] Review failed unexpectedly: {exc}")
        return _simple_review(requirements, test_cases)


def should_regenerate(state: AgentState) -> str:
    """Decide whether the workflow should iterate again."""
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 2)

    if iteration >= max_iterations:
        print(f"\n[Workflow] Reached max iterations ({max_iterations}).")
        return "end"

    if state.get("review_passed", False):
        return "end"

    return "regenerate"


def increment_iteration(state: AgentState) -> dict:
    """Increment the iteration counter."""
    return {"iteration_count": state.get("iteration_count", 0) + 1}


def _simple_review(requirements: List[dict], test_cases: List[dict]) -> dict:
    """Fallback review when the LLM-based reviewer is unavailable."""
    print("  [INFO] Falling back to rule-based review.")

    comments = []
    passed = True
    score = 100

    requirement_ids = {req["id"] for req in requirements if "id" in req}
    test_case_requirement_ids = set()
    for test_case in test_cases:
        test_case_id = test_case.get("id", "")
        if test_case_id.startswith("TC_"):
            parts = test_case_id.split("_")
            if len(parts) > 1:
                test_case_requirement_ids.add(f"REQ_{parts[1]}")

    missing_requirements = requirement_ids - test_case_requirement_ids
    if missing_requirements:
        passed = False
        score -= 20
        comments.append(
            {
                "type": "missing_coverage",
                "severity": "high",
                "message": f"Missing test-case coverage for requirements: {sorted(missing_requirements)}",
            }
        )

    for test_case in test_cases:
        if not test_case.get("expected"):
            score -= 5
            comments.append(
                {
                    "type": "missing_expected",
                    "severity": "medium",
                    "message": f"{test_case.get('id', 'UNKNOWN_TC')} has no expected result.",
                }
            )

    if len(test_cases) < len(requirements):
        passed = False
        score -= 20
        comments.append(
            {
                "type": "insufficient_cases",
                "severity": "high",
                "message": (
                    f"Generated test cases ({len(test_cases)}) are fewer than "
                    f"requirements ({len(requirements)})."
                ),
            }
        )

    score = max(score, 0)

    return {
        "review_passed": passed,
        "review_score": score,
        "review_comments": comments,
        "review_suggestions": [],
        "current_step": "reviewed",
        "agent_messages": [
            {
                "role": "reviewer",
                "content": f"Fallback review {'passed' if passed else 'failed'} with score {score}/100.",
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


def generate_script_node(state: AgentState) -> dict:
    """Generate a Midscene/Playwright script."""
    print("\n[Agent] Generating Midscene test script...")

    test_cases = state.get("test_cases") or []
    page_url = state.get("page_url", "https://example.com")

    if not test_cases:
        print("  [WARN] No test cases available; skipping script generation.")
        return {"generated_script": None, "current_step": "script_skipped"}

    scenario_config = state.get("scenario_config")

    generator = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR), use_llm=False)
    script_path = generator.generate(
        test_cases,
        page_url=page_url,
        scenario_config=scenario_config,
    )

    abs_path = os.path.abspath(script_path)
    exists = os.path.exists(abs_path)
    print(f"  [DEBUG] Script path: {script_path}")
    print(f"  [DEBUG] Absolute path: {abs_path}")
    print(f"  [DEBUG] Exists: {exists}")

    if not exists:
        print("  [ERROR] Generated script file does not exist.")
        return {"generated_script": None, "current_step": "script_failed"}

    print(f"  [OK] Script generated: {script_path}")
    return {
        "generated_script": script_path,
        "current_step": "script_generated",
        "agent_messages": [
            {"role": "generator", "content": f"Generated test script: {script_path}"}
        ],
    }


def execute_tests_node(state: AgentState) -> dict:
    """Execute the generated browser tests."""
    print("\n[Agent] Executing test script...")

    script_path = state.get("generated_script")
    if not script_path:
        print("  [WARN] No generated script available; skipping execution.")
        return {"execution_results": None, "current_step": "execution_skipped"}

    abs_path = os.path.abspath(script_path)
    print(f"  [DEBUG] Script path: {script_path}")
    print(f"  [DEBUG] Absolute path: {abs_path}")
    print(f"  [DEBUG] Exists: {os.path.exists(abs_path)}")

    executor = TestExecutor(
        config={
            "headed": True,
            "timeout": 180000,
        }
    )
    result = executor.run_tests(script_path)
    scenario_config = state.get("scenario_config") or {}
    if scenario_config:
        result["scenario_type"] = scenario_config.get("scenario_type")
        result["success_signal"] = scenario_config.get("success_signal")
        result["metadata"] = {
            "scenario_type": scenario_config.get("scenario_type"),
            "success_signal": scenario_config.get("success_signal"),
            "manual_wait": bool(
                scenario_config.get("manual_wait")
                or scenario_config.get("mfa_mode") == "manual_wait"
            ),
            "forbidden_actions": scenario_config.get("forbidden_actions") or [],
        }

    if result.get("status") == "error" and result.get("total", 0) == 0:
        reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")
        fallback_test_cases = state.get("test_cases") or []
        if scenario_config.get("scenario_type") == "login_only" and fallback_test_cases:
            fallback_test_cases = fallback_test_cases[:1]
        fallback = reporter.write_fallback_results(
            test_cases=fallback_test_cases,
            error_message=(
                result.get("error")
                or result.get("stderr")
                or result.get("raw_output")
                or "Test execution failed."
            ),
            script_path=script_path,
            metadata=result.get("metadata"),
        )
        if fallback["created"] > 0:
            result.update(
                {
                    "status": "failed",
                    "total": fallback["total"],
                    "passed": fallback["passed"],
                    "failed": fallback["failed"],
                    "skipped": fallback["skipped"],
                }
            )
            print(
                "  [WARN] Executor did not emit test results; "
                f"wrote {fallback['created']} fallback Allure results."
            )

    print("  [OK] Execution finished")
    print(f"       Total: {result['total']}")
    print(f"       Passed: {result['passed']}")
    print(f"       Failed: {result['failed']}")
    print(f"       Duration: {result['duration']}s")

    return {
        "execution_results": result,
        "current_step": "tests_executed",
        "agent_messages": [
            {
                "role": "executor",
                "content": f"Execution finished: {result['passed']}/{result['total']} passed.",
            }
        ],
    }


def generate_report_node(state: AgentState) -> dict:
    """Generate the Allure report."""
    print("\n[Agent] Generating Allure report...")

    reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")
    if not reporter.check_allure_installed():
        print("  [WARN] Allure is not installed; skipping report generation.")
        print("  Install with: npm install -g allure-commandline")
        return {"allure_report_path": None, "current_step": "report_skipped"}

    results_dir = Path(reporter.results_dir)
    has_result_files = results_dir.exists() and any(results_dir.glob("*result*.json"))
    execution_results = state.get("execution_results") or {}

    if not has_result_files and execution_results.get("tests"):
        created = reporter.write_results_from_execution(
            execution_results=execution_results,
            script_path=state.get("generated_script"),
        )
        if created["created"] > 0:
            print(
                "  [INFO] Materialized "
                f"{created['created']} Allure result files from execution results."
            )

    result = reporter.generate_report()
    if result["status"] == "success":
        print(f"  [OK] Report generated: {result['report_path']}")
        return {
            "allure_report_path": result["report_path"],
            "current_step": "report_generated",
            "agent_messages": [
                {"role": "reporter", "content": "Generated Allure report successfully."}
            ],
        }

    print(f"  [WARN] Report generation failed: {result['error']}")
    return {"allure_report_path": None, "current_step": "report_failed"}


def build_workflow() -> StateGraph:
    """Build the full LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze_requirements", analyze_requirements_node)
    workflow.add_node("generate_test_cases", generate_test_cases_node)
    workflow.add_node(
        "generate_test_case_for_requirement",
        generate_test_case_for_requirement_node,
        input_schema=SingleRequirementGenerationState,
    )
    workflow.add_node("finalize_test_case_generation", finalize_test_case_generation_node)
    workflow.add_node("review_test_cases", review_test_cases_node)
    workflow.add_node("increment_iteration", increment_iteration)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("execute_tests", execute_tests_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.set_entry_point("analyze_requirements")

    workflow.add_edge("analyze_requirements", "generate_test_cases")
    workflow.add_conditional_edges("generate_test_cases", fan_out_requirements)
    workflow.add_edge("generate_test_case_for_requirement", "finalize_test_case_generation")
    workflow.add_edge("finalize_test_case_generation", "review_test_cases")

    workflow.add_conditional_edges(
        "review_test_cases",
        should_regenerate,
        {
            "regenerate": "increment_iteration",
            "end": "generate_script",
        },
    )

    workflow.add_edge("increment_iteration", "generate_test_cases")
    workflow.add_edge("generate_script", "execute_tests")
    workflow.add_edge("execute_tests", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow


def run_workflow(
    requirement_text: str,
    max_iterations: int = 2,
    page_url: str = "https://example.com",
    scenario_config: Optional[ScenarioConfig] = None,
) -> AgentState:
    """Run the end-to-end workflow."""
    resolved_page_url = page_url
    if scenario_config and scenario_config.get("page_url"):
        resolved_page_url = str(scenario_config["page_url"])

    initial_state: AgentState = {
        "requirement_text": requirement_text,
        "requirements": None,
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
        "page_url": resolved_page_url,
        "scenario_config": scenario_config,
        "execution_results": None,
        "allure_report_path": None,
        "current_step": "init",
        "agent_messages": [],
    }

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
