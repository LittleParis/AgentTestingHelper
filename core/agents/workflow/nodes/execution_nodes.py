"""Test execution and report generation nodes."""

import os
from pathlib import Path

from core.automation.allure_reporter import AllureReporter
from core.automation.test_executor import TestExecutor
from core.agents.workflow.scenarios import is_login_only_scenario
from core.agents.workflow.utils import build_executor_env_overrides
from core.models.workflow import AgentState


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

    scenario_config = state.get("scenario_config") or {}
    executor_config = {
        "headed": True,
        "timeout": 180000,
    }
    env_overrides = build_executor_env_overrides(scenario_config)
    if env_overrides:
        executor_config["env_overrides"] = env_overrides
        print("  [INFO] Injected requirement-document credentials into the execution environment.")

    executor = TestExecutor(config=executor_config)
    result = executor.run_tests(script_path)
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