"""Helpers for classifying execution failures into stable categories."""

from __future__ import annotations

from typing import Dict, Iterable, List

from core.models.runtime import ExecutionFailureCategory, FailureAnalysisResult


def analyze_execution_failure(
    *,
    status: str,
    error: str | None = None,
    trace: str | None = None,
    raw_output: str | None = None,
    required_env_vars: Iterable[str] | None = None,
    env_values: Dict[str, str] | None = None,
) -> FailureAnalysisResult:
    """Classify a workflow or test failure into a stable category."""

    error_text = " ".join(
        [
            status or "",
            error or "",
            trace or "",
            raw_output or "",
        ]
    ).lower()

    missing_env_vars: List[str] = []
    if required_env_vars and env_values is not None:
        missing_env_vars = [
            env_name
            for env_name in required_env_vars
            if not str(env_values.get(env_name, "")).strip()
        ]
    if missing_env_vars:
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.CREDENTIAL_ISSUE,
            summary=f"Missing runtime credentials: {', '.join(missing_env_vars)}.",
            confidence=0.96,
            evidence=[f"Missing env var: {env_name}" for env_name in missing_env_vars],
            suggested_action="Provide the required credential environment variables before execution.",
        )

    if any(token in error_text for token in ["manual_verification_timeout", "timed out", "timeout", "timeoutexpired"]):
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.TIMEOUT_ISSUE,
            summary="Execution timed out before the browser flow completed.",
            confidence=0.9,
            evidence=_compact_evidence(error, trace, raw_output),
            suggested_action="Increase timeout or reduce manual verification steps for the benchmark flow.",
        )

    if any(token in error_text for token in ["process.env", "credential", "login_username", "login_password", "authentication failed"]):
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.CREDENTIAL_ISSUE,
            summary="Execution failed because runtime credentials were unavailable or rejected.",
            confidence=0.82,
            evidence=_compact_evidence(error, trace, raw_output),
            suggested_action="Verify the injected login credentials and the credential env var mapping.",
        )

    if any(token in error_text for token in ["locator", "element", "selector", "not visible", "strict mode violation"]):
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.ELEMENT_LOCATION_ISSUE,
            summary="Execution failed while locating or interacting with a page element.",
            confidence=0.86,
            evidence=_compact_evidence(error, trace, raw_output),
            suggested_action="Inspect the selector catalog or prefer a more deterministic native action for this step.",
        )

    if any(token in error_text for token in ["expect(", "expect ", "assert", "toequal", "tobevisible", "text visible", "url changed"]):
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.ASSERTION_ISSUE,
            summary="Execution reached the validation stage but the assertion did not pass.",
            confidence=0.8,
            evidence=_compact_evidence(error, trace, raw_output),
            suggested_action="Review the expected result wording and final assertions for this test case.",
        )

    if any(token in error_text for token in ["jsondecodeerror", "structured", "schema", "pydantic", "response_format"]):
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.LLM_OUTPUT_ISSUE,
            summary="An LLM structured-output or schema validation problem blocked the run.",
            confidence=0.85,
            evidence=_compact_evidence(error, trace, raw_output),
            suggested_action="Inspect the structured response diagnostics and tighten the prompt/schema contract.",
        )

    if any(token in error_text for token in ["allure", "playwright", "npx", "enoent", "not recognized", "module not found"]):
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.ENVIRONMENT_ISSUE,
            summary="The local execution environment is missing a required dependency or tool.",
            confidence=0.88,
            evidence=_compact_evidence(error, trace, raw_output),
            suggested_action="Install the missing runtime dependency and verify the local toolchain.",
        )

    if status == "success":
        return FailureAnalysisResult(
            category=ExecutionFailureCategory.NONE,
            summary="Execution completed successfully.",
            confidence=1.0,
            evidence=[],
            suggested_action=None,
        )

    return FailureAnalysisResult(
        category=ExecutionFailureCategory.EXECUTION_ISSUE,
        summary="Execution failed for a non-classified runtime reason.",
        confidence=0.55,
        evidence=_compact_evidence(error, trace, raw_output),
        suggested_action="Inspect the raw output and test attachments for the next debugging step.",
    )


def _compact_evidence(*values: str | None) -> List[str]:
    evidence: List[str] = []
    for value in values:
        if not value:
            continue
        single_line = " ".join(str(value).split())
        if single_line:
            evidence.append(single_line[:240])
    return evidence[:3]

