"""Requirement analysis nodes."""

from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.workflow import AgentState


def analyze_requirements_node(state: AgentState) -> dict:
    """Analyze the requirement document."""
    print("\n[Agent] Analyzing requirements...")

    analyzer = RequirementAnalyzer()
    result = analyzer.analyze(state["requirement_text"])
    requirements = result.get("requirements", [])

    return {
        "requirements": requirements,
        "planned_requirements": None,
        "test_strategy": None,
        "requirement_summary": result.get("summary", ""),
        "current_step": "requirement_analyzed",
        "agent_messages": [
            {
                "role": "analyzer",
                "content": f"Identified {len(requirements)} requirements.",
            }
        ],
    }