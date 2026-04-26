"""Script generation nodes."""

import os

from core.automation.midscene_generator import MidsceneScriptGenerator
from core.utils.project_paths import GENERATED_TESTS_DIR
from core.models.workflow import AgentState


def plan_script_generation_node(state: AgentState) -> dict:
    """Plan structured script execution before rendering code."""
    print("\n[Agent] Planning script generation...")

    test_cases = state.get("test_cases") or []
    page_url = state.get("page_url", "https://example.com")
    scenario_config = state.get("scenario_config")

    if not test_cases:
        print("  [WARN] No test cases available; skipping script planning.")
        return {"script_plans": None, "current_step": "script_plan_skipped"}

    generator = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR), use_llm=True)
    script_plans = generator.plan_script_generation(
        test_cases,
        page_url=page_url,
        scenario_config=scenario_config,
        strategy_plan=state.get("test_strategy"),
    )

    print(f"  [OK] Planned {len(script_plans)} script execution plan(s).")
    return {
        "script_plans": [plan.model_dump() for plan in script_plans],
        "current_step": "script_planned",
        "agent_messages": [
            {
                "role": "script_planner",
                "content": f"Planned {len(script_plans)} structured script execution plan(s).",
            }
        ],
    }


def generate_script_node(state: AgentState) -> dict:
    """Generate a Midscene/Playwright script."""
    print("\n[Agent] Generating Midscene test script...")

    test_cases = state.get("test_cases") or []
    page_url = state.get("page_url", "https://example.com")

    if not test_cases:
        print("  [WARN] No test cases available; skipping script generation.")
        return {"generated_script": None, "current_step": "script_skipped"}

    scenario_config = state.get("scenario_config")

    generator = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR), use_llm=True)
    script_path = generator.generate(
        test_cases,
        page_url=page_url,
        scenario_config=scenario_config,
        strategy_plan=state.get("test_strategy"),
        script_plans=state.get("script_plans"),
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