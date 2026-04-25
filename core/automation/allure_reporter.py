"""Helpers for generating and opening Allure reports."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional


class AllureReporter:
    """Generate and manage Allure reports."""

    def __init__(self, results_dir: str = "allure-results", report_dir: str = "allure-report"):
        self.results_dir = Path(results_dir)
        self.report_dir = Path(report_dir)

    def generate_report(self, clean: bool = True, single_file: bool = True) -> dict:
        """Generate an Allure HTML report."""
        if not self.results_dir.exists():
            return {
                "status": "error",
                "report_path": None,
                "error": f"Results directory does not exist: {self.results_dir}",
            }

        result_files = list(self.results_dir.glob("*"))
        if not result_files:
            return {
                "status": "error",
                "report_path": None,
                "error": "Results directory is empty, no test results found.",
            }

        allure_cmd = self._resolve_allure_command()
        if not allure_cmd:
            return {
                "status": "error",
                "report_path": None,
                "error": "Allure command is not available.",
            }

        try:
            if clean and self.report_dir.exists():
                shutil.rmtree(self.report_dir)

            cmd = [
                *allure_cmd,
                "generate",
                str(self.results_dir),
                "-o",
                str(self.report_dir),
                "--clean",
            ]
            if single_file:
                cmd.append("--single-file")

            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "report_path": None,
                    "error": f"Failed to generate report: {result.stderr or result.stdout}",
                }

            return {
                "status": "success",
                "report_path": str(self.report_dir.resolve()),
                "error": None,
                "summary": self.get_report_summary(),
            }

        except Exception as exc:
            return {
                "status": "error",
                "report_path": None,
                "error": str(exc),
            }

    def open_report(self) -> dict:
        """Open a generated report in the default browser."""
        if not self.report_dir.exists():
            return {
                "status": "error",
                "error": f"Report directory does not exist: {self.report_dir}",
            }

        index_file = self.report_dir / "index.html"
        if not index_file.exists():
            return {
                "status": "error",
                "error": f"Report file does not exist: {index_file}",
            }

        try:
            url = f"file:///{index_file.resolve().as_posix()}"
            webbrowser.open(url)
            return {
                "status": "success",
                "error": None,
                "message": f"Opened report in browser: {url}",
                "url": url,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    def clean_results(self) -> None:
        """Delete the results directory."""
        if self.results_dir.exists():
            shutil.rmtree(self.results_dir)
            print(f"Cleaned results directory: {self.results_dir}")

    def write_fallback_results(
        self,
        test_cases: list[dict],
        error_message: str,
        script_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create synthetic failed Allure results when Playwright emits none."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        now_ms = int(time.time() * 1000)
        package_name = Path(script_path).name if script_path else "generated.spec.ts"

        for index, test_case in enumerate(test_cases, start=1):
            test_name = f"{test_case.get('id', f'TC_{index:03d}')}: {test_case.get('title', 'Unnamed test')}"
            result = {
                "uuid": str(uuid.uuid4()),
                "name": test_name,
                "status": "failed",
                "statusDetails": {
                    "message": error_message,
                    "trace": error_message,
                },
                "stage": "finished",
                "steps": self._build_execution_steps(
                    "failed",
                    now_ms + index,
                    now_ms + index + 1,
                    metadata,
                ),
                "attachments": [],
                "parameters": [],
                "labels": [
                    {"name": "language", "value": "javascript"},
                    {"name": "framework", "value": "playwright"},
                    {"name": "package", "value": package_name},
                    {"name": "suite", "value": package_name},
                ]
                + self._build_metadata_labels(metadata),
                "links": [],
                "start": now_ms + index,
                "stop": now_ms + index + 1,
                "fullName": f"{package_name}#{test_case.get('id', f'TC_{index:03d}')}",
                "titlePath": [package_name],
            }

            result_file = self.results_dir / f"{uuid.uuid4()}-result.json"
            with open(result_file, "w", encoding="utf-8") as file:
                json.dump(result, file, ensure_ascii=False, indent=2)
            created += 1

        return {
            "created": created,
            "failed": created,
            "passed": 0,
            "broken": 0,
            "skipped": 0,
            "total": created,
        }

    def write_results_from_execution(
        self,
        execution_results: dict,
        script_path: Optional[str] = None,
    ) -> dict:
        """Materialize parsed execution results into Allure result files."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        tests = execution_results.get("tests") or []
        if not tests:
            return {
                "created": 0,
                "passed": 0,
                "failed": 0,
                "broken": 0,
                "skipped": 0,
                "total": 0,
            }

        summary = {
            "created": 0,
            "passed": 0,
            "failed": 0,
            "broken": 0,
            "skipped": 0,
            "total": 0,
        }
        package_name = Path(script_path).name if script_path else "generated.spec.ts"
        base_time_ms = int(time.time() * 1000)
        run_error = (
            execution_results.get("error")
            or execution_results.get("stderr")
            or ""
        )
        metadata = execution_results.get("metadata") or {}

        for index, test in enumerate(tests, start=1):
            raw_status = str(test.get("status", "")).lower()
            status = self._map_execution_status(raw_status)
            duration_ms = max(1, self._to_duration_ms(test.get("duration")))
            start_ms = base_time_ms + index
            stop_ms = start_ms + duration_ms
            test_name = test.get("name") or f"TC_{index:03d}"
            status_details = self._build_status_details(test, status, run_error)

            result = {
                "uuid": str(uuid.uuid4()),
                "historyId": f"{package_name}:{test_name}",
                "fullName": f"{package_name}#{test_name}",
                "name": test_name,
                "status": status,
                "stage": "finished",
                "start": start_ms,
                "stop": stop_ms,
                "steps": self._build_execution_steps(status, start_ms, stop_ms, metadata),
                "attachments": self._materialize_attachments(test.get("attachments") or []),
                "parameters": [],
                "labels": [
                    {"name": "language", "value": "javascript"},
                    {"name": "framework", "value": "playwright"},
                    {"name": "package", "value": package_name},
                    {"name": "suite", "value": package_name},
                    {"name": "host", "value": "local"},
                ]
                + self._build_metadata_labels(metadata),
                "links": [],
                "titlePath": [package_name],
            }
            if status_details:
                result["statusDetails"] = status_details

            result_file = self.results_dir / f"{uuid.uuid4()}-result.json"
            with open(result_file, "w", encoding="utf-8") as file:
                json.dump(result, file, ensure_ascii=False, indent=2)

            summary["created"] += 1
            summary["total"] += 1
            summary[status if status in summary else "broken"] += 1

        self._write_environment_file()
        return summary

    def get_report_summary(self) -> dict:
        """Summarize Allure result files by status."""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "broken": 0,
            "skipped": 0,
        }

        if not self.results_dir.exists():
            return summary

        for result_file in self.results_dir.glob("*result*.json"):
            try:
                with open(result_file, "r", encoding="utf-8") as file:
                    result = json.load(file)
            except (OSError, json.JSONDecodeError):
                continue

            status = str(result.get("status", "")).lower()
            if status in summary:
                summary[status] += 1
            else:
                summary["broken"] += 1
            summary["total"] += 1

        return summary

    def check_allure_installed(self) -> bool:
        """Return whether an Allure CLI is available."""
        allure_cmd = self._resolve_allure_command()
        if not allure_cmd:
            return False

        try:
            result = subprocess.run(
                [*allure_cmd, "--version"],
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode == 0
        except Exception:
            return False

    def _resolve_allure_command(self) -> Optional[list[str]]:
        """Prefer the locally installed Allure binary, then fall back to PATH."""
        local_cmd = Path("node_modules") / ".bin" / "allure.cmd"
        local_sh = Path("node_modules") / ".bin" / "allure"

        if local_cmd.exists():
            return [str(local_cmd.resolve())]
        if local_sh.exists():
            return [str(local_sh.resolve())]

        system_cmd = shutil.which("allure")
        if system_cmd:
            return [system_cmd]

        system_cmd = shutil.which("allure.cmd")
        if system_cmd:
            return [system_cmd]

        return None

    def _build_status_details(self, test: dict, status: str, run_error: str) -> Optional[dict]:
        """Build a compact Allure status details block for non-passing tests."""
        if status == "passed":
            return None

        message = (
            test.get("error")
            or test.get("message")
            or test.get("trace")
            or run_error
            or f"Test finished with status: {status}"
        )
        return {
            "message": str(message)[:2000],
            "trace": str(message),
        }

    def _materialize_attachments(self, attachments: list[dict]) -> list[dict]:
        """Copy execution attachments into allure-results and return Allure references."""
        materialized: list[dict] = []
        for attachment in attachments:
            source_path = attachment.get("path")
            if not source_path:
                continue

            source = Path(source_path)
            if not source.exists():
                continue

            suffix = source.suffix or ".bin"
            target_name = f"{uuid.uuid4()}-attachment{suffix}"
            target_path = self.results_dir / target_name
            shutil.copyfile(source, target_path)
            materialized.append(
                {
                    "name": attachment.get("name") or source.name,
                    "source": target_name,
                    "type": attachment.get("contentType") or "application/octet-stream",
                }
            )

        return materialized

    def _build_metadata_labels(self, metadata: Optional[dict]) -> list[dict]:
        """Translate execution metadata into Allure labels."""
        if not metadata:
            return []

        labels: list[dict] = []
        scenario_type = metadata.get("scenario_type")
        if scenario_type:
            labels.append({"name": "tag", "value": str(scenario_type)})

        success_signal = metadata.get("success_signal") or {}
        success_value = success_signal.get("value")
        if success_value:
            labels.append({"name": "feature", "value": f"success_signal:{success_value}"})

        if metadata.get("manual_wait"):
            labels.append({"name": "story", "value": "manual_verification_wait"})

        return labels

    def _build_execution_steps(
        self,
        status: str,
        start_ms: int,
        stop_ms: int,
        metadata: Optional[dict],
    ) -> list[dict]:
        """Create minimal readable steps for imported execution results."""
        steps = [
            {
                "name": "Imported from Playwright JSON execution result",
                "status": status,
                "stage": "finished",
                "start": start_ms,
                "stop": stop_ms,
            }
        ]

        if not metadata:
            return steps

        scenario_type = metadata.get("scenario_type")
        if scenario_type:
            steps.append(
                {
                    "name": f"Scenario type: {scenario_type}",
                    "status": status,
                    "stage": "finished",
                    "start": start_ms,
                    "stop": stop_ms,
                }
            )

        if metadata.get("manual_wait"):
            steps.append(
                {
                    "name": "Entered manual verification wait",
                    "status": status,
                    "stage": "finished",
                    "start": start_ms,
                    "stop": stop_ms,
                }
            )

        success_signal = metadata.get("success_signal") or {}
        if success_signal.get("value"):
            steps.append(
                {
                    "name": f"Success signal: {success_signal['value']}",
                    "status": status,
                    "stage": "finished",
                    "start": start_ms,
                    "stop": stop_ms,
                }
            )

        return steps

    def _map_execution_status(self, raw_status: str) -> str:
        """Map Playwright JSON reporter statuses to Allure statuses."""
        if raw_status in {"expected", "passed"}:
            return "passed"
        if raw_status in {"skipped", "interrupted"}:
            return "skipped"
        if raw_status in {"timedout", "timeout"}:
            return "broken"
        if raw_status in {"unexpected", "failed"}:
            return "failed"
        return "broken"

    def _to_duration_ms(self, duration: object) -> int:
        """Convert a duration value to milliseconds."""
        if duration is None:
            return 0
        if isinstance(duration, (int, float)):
            # Playwright JSON reporter uses milliseconds, but some fallbacks store seconds.
            return int(duration if duration > 10 else duration * 1000)
        return 0

    def _write_environment_file(self) -> None:
        """Write a minimal environment file for the generated report."""
        environment_file = self.results_dir / "environment.properties"
        with open(environment_file, "w", encoding="utf-8") as file:
            file.write("Browser=Chromium\n")
            file.write("Platform=Windows\n")
            file.write("Framework=Playwright + Midscene\n")
            file.write(f"Execution.Date={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("Test.Type=UI Automation\n")


def generate_allure_report(results_dir: str = "allure-results", open_browser: bool = False) -> dict:
    """Convenience wrapper for generating an Allure report."""
    reporter = AllureReporter(results_dir=results_dir)

    if not reporter.check_allure_installed():
        return {
            "status": "error",
            "error": "Allure is not installed. Run npm install allure-commandline or install it globally.",
        }

    result = reporter.generate_report()
    if result["status"] == "success" and open_browser:
        reporter.open_report()

    return result
