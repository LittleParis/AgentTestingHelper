"""Test executor for running generated Midscene/Playwright scripts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional


class TestExecutor:
    """Run Playwright tests and normalize the execution results."""

    __test__ = False

    DEFAULT_CONFIG = {
        "browser": "chromium",
        "headed": False,
        "timeout": 120000,
        "retries": 0,
        "workers": 1,
        "screenshot_on_failure": True,
        "screenshot_on_success": False,
        "reporter": "json",
        "output_dir": "test-results",
        "browsers_path": None,
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._last_results: Optional[Dict] = None

    def run_tests(self, script_path: str) -> Dict:
        """Run a generated script and return normalized execution data."""
        abs_path = str(Path(script_path).resolve())
        if not os.path.exists(abs_path):
            return {
                "status": "error",
                "error": f"Script path not found: {script_path}",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0,
                "tests": [],
            }

        start_time = time.time()
        try:
            env = os.environ.copy()
            if self.config.get("browsers_path"):
                env["PLAYWRIGHT_BROWSERS_PATH"] = str(self.config["browsers_path"])

            project_root = self._get_project_root()
            cmd_list = self._build_playwright_command_args(script_path)
            print(f"  [DEBUG] Running command: {' '.join(cmd_list)}")

            result = subprocess.run(
                cmd_list,
                capture_output=True,
                timeout=self._calculate_timeout(),
                shell=False,
                cwd=project_root,
                env=env,
                encoding="utf-8",
                errors="replace",
            )

            duration = time.time() - start_time
            print(f"  [DEBUG] Execution duration: {duration:.2f}s")
            print(f"  [DEBUG] Return code: {result.returncode}")

            parsed = self._parse_json_report_text(result.stdout)
            if parsed["total"] == 0 and not parsed.get("error"):
                fallback = self._parse_text_output_fallback(result.stdout + result.stderr)
                if fallback["total"] > 0:
                    parsed = fallback

            parsed["duration"] = round(duration, 2)
            parsed["status"] = self._determine_execution_status(result.returncode, parsed)
            parsed["raw_output"] = result.stdout + result.stderr
            parsed["stdout"] = result.stdout
            parsed["stderr"] = result.stderr
            parsed["returncode"] = result.returncode
            if parsed["status"] == "error" and not parsed.get("error"):
                parsed["error"] = result.stderr.strip() or result.stdout.strip() or "Test execution failed."

            print(
                "  [DEBUG] Parsed result: "
                f"total={parsed['total']}, passed={parsed['passed']}, failed={parsed['failed']}"
            )

            self._last_results = parsed
            return parsed

        except subprocess.TimeoutExpired as exc:
            stdout = ""
            stderr = ""
            if getattr(exc, "stdout", None):
                stdout = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode("utf-8", errors="replace")
            if getattr(exc, "stderr", None):
                stderr = exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode("utf-8", errors="replace")
            return {
                "status": "error",
                "error": "Test execution timeout",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": round(time.time() - start_time, 2),
                "tests": [],
                "stdout": stdout,
                "stderr": stderr,
                "raw_output": stdout + stderr,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": round(time.time() - start_time, 2),
                "tests": [],
            }

    def run_single_test(self, script_path: str, test_name: str) -> Dict:
        """Run a single test via Playwright grep filtering."""
        config = {**self.config, "grep": test_name}
        return TestExecutor(config).run_tests(script_path)

    def _parse_json_report(self, json_path: str) -> Dict:
        """Parse a Playwright JSON report from disk."""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": [],
            "error": None,
        }

        try:
            with open(json_path, "r", encoding="utf-8") as file:
                report = json.load(file)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"  [DEBUG] Failed to parse JSON report file: {exc}")
            return results

        return self._parse_report_object(report)

    def _parse_json_report_text(self, report_text: str) -> Dict:
        """Parse a Playwright JSON reporter payload from stdout."""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": [],
            "error": None,
        }

        if not report_text or not report_text.strip():
            return results

        try:
            report = json.loads(report_text)
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"  [DEBUG] Failed to parse JSON stdout: {exc}")
            return results

        return self._parse_report_object(report)

    def _parse_report_object(self, report: Dict) -> Dict:
        """Normalize a parsed Playwright report object."""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": [],
            "error": None,
        }

        stats = report.get("stats", {})
        results["passed"] = stats.get("expected", 0)
        results["failed"] = stats.get("unexpected", 0) + stats.get("flaky", 0)
        results["skipped"] = stats.get("skipped", 0)
        results["total"] = results["passed"] + results["failed"] + results["skipped"]

        for suite in report.get("suites", []):
            self._extract_tests_from_suite(suite, results["tests"])

        errors = report.get("errors") or []
        if errors:
            first_error = errors[0]
            if isinstance(first_error, dict):
                results["error"] = first_error.get("message") or first_error.get("stack")
            else:
                results["error"] = str(first_error)

        return results

    def _extract_tests_from_suite(self, suite: Dict, tests_list: List[Dict]) -> None:
        """Recursively extract test-level details from nested suites."""
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                error_details = self._extract_test_error_details(test)
                attachments = self._extract_test_attachments(test)
                tests_list.append(
                    {
                        "name": test.get("title", spec.get("title", "unknown")),
                        "status": test.get("status", "unknown"),
                        "duration": test.get("duration", 0),
                        "attachments": attachments,
                        **error_details,
                    }
                )

        for child_suite in suite.get("suites", []):
            self._extract_tests_from_suite(child_suite, tests_list)

    def _extract_test_error_details(self, test: Dict) -> Dict:
        """Extract the most useful single-test failure details from Playwright JSON."""
        for result in test.get("results", []) or []:
            errors = result.get("errors") or []
            if not errors:
                continue

            first_error = errors[0]
            if isinstance(first_error, dict):
                message = first_error.get("message") or first_error.get("value") or ""
                trace = first_error.get("stack") or message
            else:
                message = str(first_error)
                trace = message

            return {
                "error": message,
                "trace": trace,
            }

        return {}

    def _extract_test_attachments(self, test: Dict) -> List[Dict]:
        """Extract attachment metadata from the final Playwright test result."""
        for result in reversed(test.get("results", []) or []):
            attachments = []
            for attachment in result.get("attachments", []) or []:
                path = attachment.get("path")
                if not path:
                    continue
                attachments.append(
                    {
                        "name": attachment.get("name") or Path(path).name,
                        "path": path,
                        "contentType": attachment.get("contentType") or "application/octet-stream",
                    }
                )
            if attachments:
                return attachments
        return []

    def _parse_text_output_fallback(self, output: str) -> Dict:
        """Fallback summary parser when JSON output is unavailable."""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": [],
            "error": None,
        }

        if not output:
            return results

        summary_passed = re.search(r"(\d+)\s+passed", output)
        summary_failed = re.search(r"(\d+)\s+failed", output)
        summary_skipped = re.search(r"(\d+)\s+skipped", output)

        results["passed"] = int(summary_passed.group(1)) if summary_passed else 0
        results["failed"] = int(summary_failed.group(1)) if summary_failed else 0
        results["skipped"] = int(summary_skipped.group(1)) if summary_skipped else 0
        results["total"] = results["passed"] + results["failed"] + results["skipped"]

        return results

    def get_execution_summary(self) -> Dict:
        """Return the latest execution summary."""
        if not self._last_results:
            return {
                "status": "no_results",
                "message": "No test execution results available",
            }

        return {
            "status": self._last_results.get("status"),
            "total": self._last_results.get("total", 0),
            "passed": self._last_results.get("passed", 0),
            "failed": self._last_results.get("failed", 0),
            "skipped": self._last_results.get("skipped", 0),
            "duration": self._last_results.get("duration", 0),
            "pass_rate": self._calculate_pass_rate(),
        }

    def get_failed_tests(self) -> List[Dict]:
        """Return failed tests from the last run."""
        if not self._last_results:
            return []
        return [test for test in self._last_results.get("tests", []) if test["status"] == "failed"]

    def get_screenshots(self) -> List[str]:
        """Return screenshots captured under the configured output directory."""
        output_dir = Path(self.config["output_dir"])
        if not output_dir.exists():
            return []

        screenshots: List[str] = []
        for pattern in ["**/*.png", "**/*.jpg"]:
            screenshots.extend(str(path) for path in output_dir.glob(pattern))
        return screenshots

    def _build_playwright_command(self, script_path: str) -> str:
        """Build a human-readable Playwright CLI command."""
        project_root = self._get_project_root()
        config_path = Path(project_root) / "config" / "playwright.config.ts"
        normalized_script_path = self._normalize_script_path(script_path, project_root)
        workers = max(int(self.config.get("workers", 1) or 1), 1)

        parts = [
            "npx playwright test",
            f'"{normalized_script_path}"',
            f"--config={config_path.as_posix()}",
            f"--timeout={self.config['timeout']}",
            f"--retries={self.config['retries']}",
            "--reporter=json",
            f"--workers={workers}",
        ]

        if self.config.get("headed"):
            parts.append("--headed")
        if self.config.get("project"):
            parts.append(f"--project={self.config['project']}")
        if self.config.get("grep"):
            parts.append(f'--grep "{self.config["grep"]}"')

        return " ".join(parts)

    def _build_playwright_command_args(self, script_path: str) -> List[str]:
        """Build subprocess-ready Playwright command arguments."""
        npx_executable = self._resolve_npx_executable()
        project_root = self._get_project_root()
        config_path = Path(project_root) / "config" / "playwright.config.ts"
        normalized_script_path = self._normalize_script_path(script_path, project_root)
        workers = max(int(self.config.get("workers", 1) or 1), 1)

        parts = [
            npx_executable,
            "playwright",
            "test",
            normalized_script_path,
            f"--config={config_path.as_posix()}",
            f"--timeout={self.config['timeout']}",
            f"--retries={self.config['retries']}",
            "--reporter=json",
            f"--workers={workers}",
        ]

        if self.config.get("headed"):
            parts.append("--headed")
        if self.config.get("project"):
            parts.append(f"--project={self.config['project']}")
        if self.config.get("grep"):
            parts.extend(["--grep", self.config["grep"]])

        return parts

    def _normalize_script_path(self, script_path: str, project_root: str) -> str:
        """Normalize script paths so Playwright matches them against testDir."""
        script = Path(script_path).resolve()
        try:
            normalized = script.relative_to(Path(project_root).resolve()).as_posix()
        except ValueError:
            normalized = script.as_posix()
        return normalized

    def _calculate_timeout(self) -> int:
        """Return subprocess timeout in seconds."""
        test_timeout_seconds = self.config.get("timeout", 60000) / 1000
        buffer_seconds = 120
        return int(test_timeout_seconds + buffer_seconds)

    def _get_project_root(self) -> str:
        """Return the repository root."""
        return str(Path(__file__).resolve().parent.parent.parent)

    def _calculate_pass_rate(self) -> float:
        """Calculate pass rate from the last execution results."""
        if not self._last_results:
            return 0.0

        total = self._last_results.get("total", 0)
        if total == 0:
            return 0.0

        passed = self._last_results.get("passed", 0)
        return round(passed / total * 100, 2)

    def _determine_execution_status(self, returncode: int, parsed: Dict) -> str:
        """Infer a stable execution status from CLI exit code and parsed results."""
        if parsed.get("failed", 0) > 0:
            return "failed"
        if returncode != 0 and parsed.get("total", 0) == 0:
            return "error"
        if returncode != 0:
            return "failed"
        return "success"

    def _resolve_npx_executable(self) -> str:
        """Resolve the npx executable with Windows compatibility."""
        return shutil.which("npx.cmd") or shutil.which("npx") or "npx.cmd"
