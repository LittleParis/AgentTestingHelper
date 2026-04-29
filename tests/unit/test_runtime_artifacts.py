from pathlib import Path

from core.automation.execution_analysis import analyze_execution_failure
from core.models.runtime import ExecutionFailureCategory, RunManifest
from main_v2 import BENCHMARK_CASES, build_run_summary, save_results


def sample_state():
    return {
        "requirements": [{"id": "REQ_001", "title": "Login"}],
        "test_strategy": {"total_suggested_case_budget": 3},
        "test_cases": [{"id": "TC_001", "requirement_id": "REQ_001"}],
        "review_passed": True,
        "review_score": 85,
        "review_comments": [],
        "review_suggestions": [],
        "iteration_count": 0,
        "script_plans": [
            {
                "testcase_id": "TC_001",
                "scenario": {
                    "scenario_type": "login_only",
                    "execution_policy": "native_first",
                },
                "steps": [
                    {"preferred_executor": "playwright_native"},
                    {"preferred_executor": "mixed"},
                ],
            }
        ],
        "generated_script": None,
        "execution_results": {
            "status": "failed",
            "total": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "duration": 3.2,
            "tests": [],
            "failure_analysis": {
                "category": "assertion_issue",
                "summary": "Assertion failed on the results page.",
            },
        },
    }


def test_failure_analysis_detects_missing_credentials():
    result = analyze_execution_failure(
        status="error",
        required_env_vars=["LOGIN_USERNAME", "LOGIN_PASSWORD"],
        env_values={"LOGIN_USERNAME": "", "LOGIN_PASSWORD": ""},
    )

    assert result.category == ExecutionFailureCategory.CREDENTIAL_ISSUE
    assert "Missing runtime credentials" in result.summary


def test_save_results_writes_stable_contract(tmp_path):
    manifest = RunManifest(
        run_id="20260427_010101",
        command="validate",
        requirement_file="examples/benchmarks/benchmark_login_success.md",
        page_url="https://global.lianlianpay.com/signin",
        output_dir=str(tmp_path / "20260427_010101"),
        execute_ui=False,
    )

    files = save_results(sample_state(), manifest=manifest, benchmark_case=BENCHMARK_CASES["login-success"])

    expected_files = {
        "requirements",
        "test_strategy",
        "test_cases",
        "review",
        "script_plan",
        "execution",
        "run_summary",
        "run_manifest",
    }
    assert expected_files.issubset(files.keys())
    for file_path in files.values():
        assert Path(file_path).exists()


def test_run_summary_includes_execution_target_counts(tmp_path):
    manifest = RunManifest(
        run_id="20260427_020202",
        command="demo",
        requirement_file="examples/benchmarks/benchmark_list_search.md",
        page_url="https://www.baidu.com",
        output_dir=str(tmp_path / "20260427_020202"),
        execute_ui=False,
        benchmark_case_id="list-search",
    )

    summary = build_run_summary(sample_state(), manifest, BENCHMARK_CASES["list-search"])

    assert summary["planned_script_count"] == 1
    assert summary["execution_target_counts"]["playwright_native"] == 1
    assert summary["execution_target_counts"]["mixed"] == 1
    assert summary["failure_category"] == "assertion_issue"
