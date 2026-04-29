"""Stable CLI entrypoint for the AI testing workflow."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from dotenv import load_dotenv

from core.agents.workflow import run_workflow
from core.automation.allure_reporter import AllureReporter
from core.models.runtime import BenchmarkCase, RunManifest
from core.models.workflow import AgentState
from core.parsers.markdown_parser import (
    extract_credential_env_names,
    extract_credentials,
    extract_page_url,
    parse_markdown,
)
from core.utils.logging_setup import configure_logging
from core.utils.project_paths import (
    ALLURE_REPORT_DIR,
    ALLURE_RESULTS_DIR,
    GENERATED_TESTS_DIR,
    LEGACY_GENERATED_TESTS_DIR,
    OUTPUT_DIR,
    PLAYWRIGHT_RESULTS_DIR,
)


BENCHMARK_CASES: dict[str, BenchmarkCase] = {
    "login-success": BenchmarkCase(
        id="login-success",
        name="Login Success Path",
        requirement_file="examples/benchmarks/benchmark_login_success.md",
        description="Bounded login flow with runtime credential injection and success-signal validation.",
        page_url="https://global.lianlianpay.com/signin",
        expected_focus=["runtime credentials", "native-first planning", "success signal assertion"],
    ),
    "form-validation": BenchmarkCase(
        id="form-validation",
        name="Form Validation Path",
        requirement_file="examples/benchmarks/benchmark_form_validation.md",
        description="Form submission with invalid input and inline validation checks.",
        page_url="https://example.com/signup",
        expected_focus=["negative cases", "field validation", "assertion clarity"],
    ),
    "list-search": BenchmarkCase(
        id="list-search",
        name="List Search Path",
        requirement_file="examples/benchmarks/benchmark_list_search.md",
        description="Search/list filtering flow with deterministic assertions on result visibility.",
        page_url="https://www.baidu.com",
        expected_focus=["query entry", "result list assertion", "benchmark stability"],
    ),
}


def _build_offline_smoke_state(requirement_text: str, page_url: str, execute_ui: bool) -> AgentState:
    """Create a deterministic workflow result for CI smoke validation."""
    return {
        "requirement_text": requirement_text,
        "requirements": [
            {
                "id": "REQ_SMOKE_001",
                "title": "Offline smoke validation",
                "description": "Deterministic fallback state used to validate CLI artifact wiring.",
                "acceptance_criteria": ["CLI writes stable output artifacts without external LLM calls."],
            }
        ],
        "planned_requirements": None,
        "test_strategy": {
            "strategy_version": "offline-smoke",
            "overall_summary": "Offline smoke mode bypassed remote LLM calls and validated CLI output contracts.",
            "requirement_strategies": [],
            "total_suggested_case_budget": 1,
            "fallback_used": True,
            "metadata": {"offline_smoke": True},
        },
        "requirement_summary": "Offline smoke requirement summary.",
        "test_cases": [
            {
                "id": "TC_SMOKE_001",
                "requirement_id": "REQ_SMOKE_001",
                "title": "Offline smoke case",
                "steps": [{"step_number": 1, "action": "Validate CLI artifact contract", "expected": "Stable files are written"}],
                "expected": "Stable files are written",
                "tags": ["smoke", "offline"],
            }
        ],
        "review_passed": True,
        "review_score": 100,
        "review_comments": [],
        "review_suggestions": [],
        "iteration_count": 0,
        "max_iterations": 0,
        "feedback": [],
        "generated_script": None,
        "script_plans": [
            {
                "testcase_id": "TC_SMOKE_001",
                "title": "Offline smoke case",
                "scenario": {
                    "scenario_type": "generic",
                    "execution_policy": "native_first",
                },
                "steps": [
                    {
                        "step_number": 1,
                        "preferred_executor": "playwright_native",
                        "action_prompt": "Validate CLI artifact contract",
                        "verify_prompt": "Stable files are written",
                    }
                ],
            }
        ],
        "page_url": page_url,
        "scenario_config": None,
        "execute_ui": execute_ui,
        "execution_results": {
            "status": "skipped",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration": 0,
            "tests": [],
            "failure_analysis": {
                "category": "none",
                "summary": "Offline smoke mode skips browser execution by design.",
                "confidence": 1.0,
                "evidence": [],
                "suggested_action": None,
            },
        },
        "allure_report_path": None,
        "current_step": "offline_smoke_completed",
        "agent_messages": [
            {
                "role": "offline_smoke",
                "content": "Offline smoke mode validated the CLI artifact contract without external dependencies.",
            }
        ],
    }


def _build_login_only_scenario_config(page_url: str | None = None) -> dict:
    """Build the default bounded login-only scenario config."""
    return {
        "scenario_type": "login_only",
        "page_url": page_url or os.getenv("LOGIN_PAGE_URL", "https://global.lianlianpay.com/signin"),
        "credentials": {
            "username_env": os.getenv("LOGIN_USERNAME_ENV", "LOGIN_USERNAME"),
            "password_env": os.getenv("LOGIN_PASSWORD_ENV", "LOGIN_PASSWORD"),
        },
        "success_signal": {
            "type": os.getenv("LOGIN_SUCCESS_SIGNAL_TYPE", "visual_text_or_logo"),
            "value": os.getenv("LOGIN_SUCCESS_SIGNAL_VALUE", "LianLian"),
        },
        "manual_wait": True,
        "mfa_mode": os.getenv("LOGIN_MFA_MODE", "manual_wait"),
        "allowed_actions": [
            "open_login_page",
            "fill_identifier",
            "fill_secret",
            "submit_login",
            "wait_manual_verification",
            "assert_login_success_signal",
            "stop_execution",
        ],
        "forbidden_actions": [
            "menu_click",
            "navigation_after_login",
            "form_submit_other_than_login",
            "logout",
            "profile_edit",
        ],
        "manual_wait_timeout_ms": int(os.getenv("LOGIN_MANUAL_WAIT_TIMEOUT_MS", "180000")),
    }


def _read_login_scenario_config() -> dict | None:
    scenario_type = os.getenv("SCENARIO_TYPE", "").strip().lower()
    if scenario_type != "login_only":
        return None
    return _build_login_only_scenario_config()


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments with backward-compatible default `run` behavior."""
    argv = list(sys.argv[1:] if argv is None else argv)
    command_names = {"run", "validate", "demo"}
    normalized_argv = argv if argv[:1] and argv[0] in command_names else ["run", *argv]

    parser = argparse.ArgumentParser(
        description="Run the AI-driven test design and UI automation workflow.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_arguments(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--requirement-file", dest="requirement_file", help="Path to the requirement markdown file.")
        subparser.add_argument("--page-url", dest="page_url", help="Optional page URL override.")
        subparser.add_argument("--output-dir", dest="output_dir", default=str(OUTPUT_DIR / "runs"), help="Directory that stores stable run artifacts.")
        subparser.add_argument("--max-iterations", dest="max_iterations", type=int, default=2, help="Maximum review/generation iterations.")
        subparser.add_argument("--clean", action="store_true", help="Clean transient runtime directories before the run.")
        subparser.add_argument("--no-open-report", action="store_true", help="Do not auto-open the Allure report after a UI run.")

    run_parser = subparsers.add_parser("run", help="Run the full workflow, including optional UI execution.")
    add_common_arguments(run_parser)
    run_parser.add_argument("--no-ui", action="store_true", help="Generate and validate artifacts without running browser automation.")

    validate_parser = subparsers.add_parser("validate", help="Validate the requirement-to-plan pipeline without UI execution.")
    add_common_arguments(validate_parser)

    demo_parser = subparsers.add_parser("demo", help="Run one of the official benchmark cases.")
    add_common_arguments(demo_parser)
    demo_parser.add_argument(
        "--demo-case",
        choices=sorted(BENCHMARK_CASES.keys()),
        default="login-success",
        help="Official benchmark case to run.",
    )
    demo_parser.add_argument("--no-ui", action="store_true", help="Prepare benchmark artifacts without running browser automation.")

    return parser.parse_args(normalized_argv)


def _resolve_requirement_file(
    scenario_config: dict | None,
    cli_requirement_file: str | None = None,
    benchmark_case: BenchmarkCase | None = None,
) -> str:
    if cli_requirement_file:
        return cli_requirement_file
    if benchmark_case:
        return benchmark_case.requirement_file
    configured = os.getenv("REQUIREMENT_FILE", "").strip()
    if configured:
        return configured
    if scenario_config and scenario_config.get("scenario_type") == "login_only":
        return "examples/requirement_login_only.md"
    return "examples/requirement_baidu.md"


def _inject_requirement_credentials(
    scenario_config: dict | None,
    requirement_text: str,
) -> tuple[dict | None, dict[str, str | None]]:
    """Merge requirement-document credentials into runtime scenario config.

    Priority:
    1. Plaintext `identifier` / `password` from the requirement
    2. `.env` or process env values resolved via the configured env names
    3. Env-name placeholders kept for runtime lookup only
    """
    extracted_credentials = extract_credentials(requirement_text)
    extracted_env_names = extract_credential_env_names(requirement_text)

    if not any(extracted_credentials.values()) and not any(extracted_env_names.values()):
        return scenario_config, extracted_credentials

    updated_config = dict(scenario_config or {})
    credentials = dict(updated_config.get("credentials") or {})
    credentials.setdefault(
        "username_env",
        extracted_env_names.get("identifier_env") or os.getenv("LOGIN_USERNAME_ENV", "LOGIN_USERNAME"),
    )
    credentials.setdefault(
        "password_env",
        extracted_env_names.get("password_env") or os.getenv("LOGIN_PASSWORD_ENV", "LOGIN_PASSWORD"),
    )
    if extracted_env_names.get("identifier_env"):
        credentials["username_env"] = extracted_env_names["identifier_env"]
    if extracted_env_names.get("password_env"):
        credentials["password_env"] = extracted_env_names["password_env"]

    if extracted_credentials.get("identifier"):
        credentials["username_value"] = extracted_credentials["identifier"]
    if extracted_credentials.get("password"):
        credentials["password_value"] = extracted_credentials["password"]
    if not credentials.get("username_value"):
        fallback_username = os.getenv(str(credentials.get("username_env") or "LOGIN_USERNAME"), "").strip()
        if fallback_username:
            credentials["username_value"] = fallback_username
    if not credentials.get("password_value"):
        fallback_password = os.getenv(str(credentials.get("password_env") or "LOGIN_PASSWORD"), "").strip()
        if fallback_password:
            credentials["password_value"] = fallback_password

    updated_config["credentials"] = credentials
    return updated_config, extracted_credentials


def _maybe_enable_login_only_scenario(
    scenario_config: dict | None,
    requirement_file: str,
    requirement_text: str,
    extracted_url: str | None,
    extracted_credentials: dict[str, str | None],
) -> dict | None:
    """Infer a bounded login-only scenario when the requirement document encodes it."""
    if scenario_config and scenario_config.get("scenario_type") == "login_only":
        if extracted_url and not scenario_config.get("page_url"):
            updated_config = dict(scenario_config)
            updated_config["page_url"] = extracted_url
            return updated_config
        return scenario_config

    file_hint = "login_only" in Path(requirement_file).stem.lower() or "login_success" in Path(requirement_file).stem.lower()
    text_lower = requirement_text.lower()
    has_execution_boundary = "execution boundary" in text_lower
    has_login_url = any(token in (extracted_url or "").lower() for token in ("/signin", "/login", "sign-in"))
    has_runtime_credentials = bool(extracted_credentials.get("identifier") and extracted_credentials.get("password"))

    if not (file_hint or (has_execution_boundary and has_login_url and has_runtime_credentials)):
        return scenario_config

    inferred_config = _build_login_only_scenario_config(page_url=extracted_url)
    if scenario_config:
        merged_config = dict(scenario_config)
        merged_config.setdefault("scenario_type", inferred_config["scenario_type"])
        merged_config.setdefault("page_url", inferred_config["page_url"])
        merged_config.setdefault("success_signal", inferred_config["success_signal"])
        merged_config.setdefault("manual_wait", inferred_config["manual_wait"])
        merged_config.setdefault("mfa_mode", inferred_config["mfa_mode"])
        merged_config.setdefault("allowed_actions", inferred_config["allowed_actions"])
        merged_config.setdefault("forbidden_actions", inferred_config["forbidden_actions"])
        merged_config.setdefault("manual_wait_timeout_ms", inferred_config["manual_wait_timeout_ms"])
        merged_credentials = dict(inferred_config.get("credentials") or {})
        merged_credentials.update(merged_config.get("credentials") or {})
        merged_config["credentials"] = merged_credentials
        return merged_config

    return inferred_config


def _hydrate_runtime_credentials(scenario_config: dict | None) -> dict | None:
    """Backfill runtime credential values from env after the scenario is known."""
    if not scenario_config:
        return None

    credentials = dict((scenario_config.get("credentials") or {}))
    if not credentials:
        return scenario_config

    username_env = str(credentials.get("username_env") or "LOGIN_USERNAME")
    password_env = str(credentials.get("password_env") or "LOGIN_PASSWORD")

    if not credentials.get("username_value"):
        username_value = os.getenv(username_env, "").strip()
        if username_value:
            credentials["username_value"] = username_value
    if not credentials.get("password_value"):
        password_value = os.getenv(password_env, "").strip()
        if password_value:
            credentials["password_value"] = password_value

    updated_config = dict(scenario_config)
    updated_config["credentials"] = credentials
    return updated_config


def clean_history_data() -> None:
    """Clean transient runtime directories without touching benchmark artifacts."""
    directories = [
        GENERATED_TESTS_DIR,
        LEGACY_GENERATED_TESTS_DIR,
        ALLURE_RESULTS_DIR,
        ALLURE_REPORT_DIR,
        PLAYWRIGHT_RESULTS_DIR,
    ]
    for directory in directories:
        if not directory.exists():
            continue
        print(f"  [clean] {directory}")
        for item in directory.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except OSError as exc:
                print(f"    - skip {item.name}: {exc}")


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _serialize_value(value.model_dump())
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _build_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _copy_generated_script(script_path: str | None, run_dir: Path) -> str | None:
    if not script_path:
        return None
    source = Path(script_path)
    if not source.exists():
        return None
    target = run_dir / "generated.spec.ts"
    shutil.copy2(source, target)
    return str(target)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(_serialize_value(payload), handle, ensure_ascii=False, indent=2)


def _execution_target_counts(script_plans: list[dict[str, Any]] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for plan in script_plans or []:
        for step in plan.get("steps") or []:
            target = str(step.get("preferred_executor") or "unknown")
            counts[target] = counts.get(target, 0) + 1
    return counts


def build_run_summary(
    state: AgentState,
    manifest: RunManifest,
    benchmark_case: BenchmarkCase | None = None,
) -> dict[str, Any]:
    """Build a concise, stable summary for the run."""
    requirements = state.get("requirements") or []
    test_strategy = state.get("test_strategy") or {}
    script_plans = state.get("script_plans") or []
    execution_results = state.get("execution_results") or {}
    failure_analysis = execution_results.get("failure_analysis") or {}
    details = []
    for plan in script_plans:
        scenario = plan.get("scenario") or {}
        details.append(
            {
                "testcase_id": plan.get("testcase_id"),
                "scenario_type": scenario.get("scenario_type"),
                "execution_policy": scenario.get("execution_policy"),
            }
        )

    return {
        "run_id": manifest.run_id,
        "benchmark_case": benchmark_case.model_dump() if benchmark_case else None,
        "requirement_count": len(requirements),
        "test_case_count": len(state.get("test_cases") or []),
        "review_score": state.get("review_score"),
        "review_passed": state.get("review_passed"),
        "iteration_count": state.get("iteration_count", 0),
        "strategy_budget": test_strategy.get("total_suggested_case_budget"),
        "planned_script_count": len(script_plans),
        "execution_target_counts": _execution_target_counts(script_plans),
        "scenario_overview": details,
        "execution_status": execution_results.get("status"),
        "failure_category": failure_analysis.get("category", "none"),
        "failure_summary": failure_analysis.get("summary"),
        "artifacts": manifest.files,
    }


def save_results(
    state: AgentState,
    *,
    manifest: RunManifest,
    benchmark_case: BenchmarkCase | None = None,
) -> dict[str, str]:
    """Persist the stable output contract for one run."""
    run_dir = Path(manifest.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    generated_script_copy = _copy_generated_script(state.get("generated_script"), run_dir)
    files = {
        "requirements": str(run_dir / "requirements.json"),
        "test_strategy": str(run_dir / "test_strategy.json"),
        "test_cases": str(run_dir / "test_cases.json"),
        "review": str(run_dir / "review.json"),
        "script_plan": str(run_dir / "script_plan.json"),
        "execution": str(run_dir / "execution.json"),
        "run_summary": str(run_dir / "run_summary.json"),
        "run_manifest": str(run_dir / "run_manifest.json"),
    }
    if generated_script_copy:
        files["generated_script"] = generated_script_copy

    _write_json(Path(files["requirements"]), {"requirements": state.get("requirements") or []})
    _write_json(Path(files["test_strategy"]), {"test_strategy": state.get("test_strategy")})
    _write_json(Path(files["test_cases"]), {"test_cases": state.get("test_cases") or []})
    _write_json(
        Path(files["review"]),
        {
            "passed": state.get("review_passed"),
            "score": state.get("review_score"),
            "comments": state.get("review_comments") or [],
            "suggestions": state.get("review_suggestions") or [],
        },
    )
    _write_json(Path(files["script_plan"]), {"script_plans": state.get("script_plans") or []})
    _write_json(Path(files["execution"]), state.get("execution_results"))

    manifest.files = files
    summary = build_run_summary(state, manifest, benchmark_case)
    _write_json(Path(files["run_summary"]), summary)
    _write_json(Path(files["run_manifest"]), manifest.model_dump())
    return files


def _print_summary(state: AgentState, manifest: RunManifest, files: dict[str, str]) -> None:
    execution_results = state.get("execution_results") or {}
    failure_analysis = execution_results.get("failure_analysis") or {}
    print("\n" + "=" * 60)
    print("Workflow completed")
    print("=" * 60)
    print(f"Run ID: {manifest.run_id}")
    print(f"Requirement file: {manifest.requirement_file}")
    print(f"UI execution: {'enabled' if manifest.execute_ui else 'disabled'}")
    print(f"Requirements: {len(state.get('requirements') or [])}")
    print(f"Test cases: {len(state.get('test_cases') or [])}")
    print(f"Review score: {state.get('review_score')}")
    print(f"Planned scripts: {len(state.get('script_plans') or [])}")
    print(f"Execution status: {execution_results.get('status')}")
    if failure_analysis:
        print(f"Failure category: {failure_analysis.get('category')}")
        print(f"Failure summary: {failure_analysis.get('summary')}")
    print("Artifacts:")
    for label, path in files.items():
        print(f"  - {label}: {path}")


def open_allure_report() -> None:
    """Open the Allure report if the toolchain is available."""
    reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")
    if not reporter.check_allure_installed():
        print("  [WARN] Allure is not installed; skip opening report.")
        return

    result = reporter.generate_report()
    if result["status"] != "success":
        print(f"  [WARN] Failed to generate report: {result['error']}")
        return

    open_result = reporter.open_report()
    if open_result["status"] == "success":
        print(f"  [OK] Report URL: {open_result['url']}")
    else:
        print(f"  [WARN] Failed to serve report: {open_result['error']}")


def _load_benchmark_case(args: argparse.Namespace) -> BenchmarkCase | None:
    if args.command != "demo":
        return None
    return BENCHMARK_CASES[args.demo_case]


def _resolve_page_url(
    args: argparse.Namespace,
    extracted_url: str | None,
    scenario_config: dict | None,
    benchmark_case: BenchmarkCase | None,
) -> str:
    return (
        args.page_url
        or extracted_url
        or (scenario_config.get("page_url") if scenario_config else None)
        or (benchmark_case.page_url if benchmark_case else None)
        or "https://www.baidu.com"
    )


def _command_execute_ui(args: argparse.Namespace) -> bool:
    if args.command == "validate":
        return False
    return not getattr(args, "no_ui", False)


def _offline_smoke_enabled() -> bool:
    return os.getenv("AI_TEST_OFFLINE_SMOKE", "").strip().lower() in {"1", "true", "yes"}


def run_command(args: argparse.Namespace) -> int:
    load_dotenv()
    benchmark_case = _load_benchmark_case(args)
    scenario_config = _read_login_scenario_config()

    print("=" * 60)
    print("AI Testing Workflow CLI")
    print("=" * 60)

    if args.clean:
        print("\n[step] Cleaning transient runtime directories...")
        clean_history_data()

    log_file = configure_logging(force=True)
    print(f"[log] {log_file}")

    requirement_file = _resolve_requirement_file(
        scenario_config,
        cli_requirement_file=args.requirement_file,
        benchmark_case=benchmark_case,
    )
    if not os.path.exists(requirement_file):
        print(f"[error] Requirement file not found: {requirement_file}")
        return 1

    requirement_text = parse_markdown(requirement_file)
    extracted_url = extract_page_url(requirement_text)
    scenario_config, extracted_credentials = _inject_requirement_credentials(scenario_config, requirement_text)
    scenario_config = _maybe_enable_login_only_scenario(
        scenario_config,
        requirement_file,
        requirement_text,
        extracted_url,
        extracted_credentials,
    )
    scenario_config = _hydrate_runtime_credentials(scenario_config)

    execute_ui = _command_execute_ui(args)
    resolved_page_url = _resolve_page_url(args, extracted_url, scenario_config, benchmark_case)
    output_root = Path(args.output_dir).expanduser().resolve()
    run_id = _build_run_id()
    run_dir = output_root / run_id
    manifest = RunManifest(
        run_id=run_id,
        command=args.command,
        requirement_file=str(Path(requirement_file).resolve()),
        page_url=resolved_page_url,
        output_dir=str(run_dir),
        execute_ui=execute_ui,
        benchmark_case_id=benchmark_case.id if benchmark_case else None,
    )

    print(f"[info] Requirement file: {requirement_file}")
    print(f"[info] Page URL: {resolved_page_url}")
    print(f"[info] Output dir: {run_dir}")
    if benchmark_case:
        print(f"[info] Benchmark: {benchmark_case.id} - {benchmark_case.name}")

    try:
        if _offline_smoke_enabled():
            print("[info] Offline smoke mode enabled; bypassing remote workflow execution.")
            final_state = _build_offline_smoke_state(
                requirement_text=requirement_text,
                page_url=resolved_page_url,
                execute_ui=execute_ui,
            )
        else:
            final_state = run_workflow(
                requirement_text=requirement_text,
                max_iterations=args.max_iterations,
                scenario_config=scenario_config,
                page_url=resolved_page_url,
                execute_ui=execute_ui,
            )
    except Exception as exc:
        print(f"[error] Workflow failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    files = save_results(final_state, manifest=manifest, benchmark_case=benchmark_case)
    _print_summary(final_state, manifest, files)

    if execute_ui and not args.no_open_report and final_state.get("execution_results", {}).get("status") != "skipped":
        open_allure_report()

    return 0


def main() -> int:
    args = _parse_args()
    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
