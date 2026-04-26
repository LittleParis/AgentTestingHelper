"""Workflow routing logic."""

from core.models.workflow import AgentState


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