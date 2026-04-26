"""Planning nodes for strategy and case budgets."""

from core.agents.case_budget_planner import CaseBudgetPlanner
from core.agents.test_strategy_planner import TestStrategyPlanner
from core.agents.workflow.scenarios import (
    is_login_only_scenario,
    build_login_only_requirement,
)
from core.models.workflow import AgentState


def plan_test_strategy_node(state: AgentState) -> dict:
    """Plan requirement-level test strategy before case budgeting."""
    print("\n[Agent] Planning test strategy...")

    requirements = state.get("requirements") or []
    if not requirements:
        return {
            "test_strategy": {
                "strategy_version": "v1",
                "overall_summary": "No requirements were available for strategy planning.",
                "requirement_strategies": [],
                "total_suggested_case_budget": 0,
                "fallback_used": True,
                "metadata": {"reason": "no_requirements"},
            },
            "current_step": "test_strategy_planned",
            "agent_messages": [
                {
                    "role": "strategy",
                    "content": "No requirements were available, so strategy planning was skipped.",
                }
            ],
        }

    planner = TestStrategyPlanner()
    strategy_plan = planner.plan(
        requirement_text=state.get("requirement_text", ""),
        analyzed_requirements=requirements,
    )

    strategy_count = len(strategy_plan.get("requirement_strategies") or [])
    total_budget = int(strategy_plan.get("total_suggested_case_budget") or 0)
    fallback_used = bool(strategy_plan.get("fallback_used"))

    print(
        "  [OK] Planned "
        f"{strategy_count} requirement strategies with suggested budget {total_budget}."
    )

    return {
        "test_strategy": strategy_plan,
        "current_step": "test_strategy_planned",
        "agent_messages": [
            {
                "role": "strategy",
                "content": (
                    f"Planned {strategy_count} requirement strategies with suggested budget {total_budget}"
                    + (" using fallback heuristics." if fallback_used else ".")
                ),
            }
        ],
    }


def plan_case_budgets_node(state: AgentState) -> dict:
    """Plan requirement-level case budgets from the analyzed requirement document."""
    print("\n[Agent] Planning flow-aware case budgets...")

    scenario_config = state.get("scenario_config")
    if is_login_only_scenario(scenario_config):
        bounded_requirement = build_login_only_requirement(scenario_config)
        bounded_requirement["generation_context"] = {
            "target_case_count": 1,
            "case_id_prefix": "001",
            "planning_mode": "bounded_login_only",
            "overall_risk": "critical",
            "coverage_focus": ["happy_path"],
        }
        bounded_requirement["flow_name"] = bounded_requirement.get("title") or bounded_requirement["id"]
        bounded_requirement["flow_type"] = "login_only"
        bounded_requirement["page_url"] = state.get("page_url") or bounded_requirement.get("page_url")
        print("  [INFO] Login-only scenario detected; skipping dynamic case-budget planning.")
        return {
            "requirements": [bounded_requirement],
            "planned_requirements": [bounded_requirement],
            "current_step": "case_budgets_planned",
            "agent_messages": [
                {
                    "role": "planner",
                    "content": "Login-only scenario detected; using a single bounded requirement.",
                }
            ],
        }

    requirements = state.get("requirements") or []
    requirement_text = state.get("requirement_text", "")
    strategy_plan = state.get("test_strategy")

    planner = CaseBudgetPlanner()
    planned_requirements = planner.plan(
        requirement_text=requirement_text,
        analyzed_requirements=requirements,
        strategy_plan=strategy_plan,
        page_url=state.get("page_url"),
    )

    total_budget = sum(
        int((requirement.get("generation_context") or {}).get("target_case_count") or 0)
        for requirement in planned_requirements
    )
    print(
        "  [OK] Planned "
        f"{len(planned_requirements)} flow requirements with a total case budget of {total_budget}."
    )

    return {
        "requirements": planned_requirements,
        "planned_requirements": planned_requirements,
        "current_step": "case_budgets_planned",
        "agent_messages": [
            {
                "role": "planner",
                "content": (
                    f"Planned {len(planned_requirements)} flow requirements "
                    f"with total case budget {total_budget}."
                ),
            }
        ],
    }