"""Review nodes."""

from core.agents.case_reviewer import CaseReviewer
from core.agents.workflow.scenarios import (
    is_login_only_scenario,
    review_login_only_test_cases,
    simple_review,
)
from core.models.workflow import AgentState


def review_test_cases_node(state: AgentState) -> dict:
    """Review generated test cases."""
    print("\n[Agent] Reviewing generated test cases...")

    requirements = state.get("requirements") or []
    test_cases = state.get("test_cases") or []
    scenario_config = state.get("scenario_config")

    if is_login_only_scenario(scenario_config):
        print("  [INFO] Login-only scenario detected; using deterministic review.")
        return review_login_only_test_cases(requirements, test_cases)

    try:
        reviewer = CaseReviewer()
        result = reviewer.review_all(requirements, test_cases)

        passed = result.get("passed", False)
        score = result.get("total_score", 0)
        details = result.get("details", [])

        all_comments: list = []
        all_suggestions: list = []

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
        return simple_review(requirements, test_cases)


def increment_iteration(state: AgentState) -> dict:
    """Increment the iteration counter."""
    return {"iteration_count": state.get("iteration_count", 0) + 1}