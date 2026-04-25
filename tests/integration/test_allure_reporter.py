"""Tests for AllureReporter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.automation.allure_reporter import AllureReporter, generate_allure_report


class TestAllureReporter:
    def test_init(self):
        reporter = AllureReporter()
        assert reporter.results_dir.name == "allure-results"
        assert reporter.report_dir.name == "allure-report"

    def test_init_custom_dirs(self):
        reporter = AllureReporter(results_dir="custom-results", report_dir="custom-report")
        assert reporter.results_dir.name == "custom-results"
        assert reporter.report_dir.name == "custom-report"

    def test_generate_report_no_results(self):
        reporter = AllureReporter(results_dir="nonexistent-results", report_dir="test-report")
        result = reporter.generate_report()

        assert result["status"] == "error"
        assert "does not exist" in result["error"]

    def test_get_report_summary_empty(self):
        reporter = AllureReporter(results_dir="nonexistent-results", report_dir="test-report")
        summary = reporter.get_report_summary()

        assert summary == {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "broken": 0,
            "skipped": 0,
        }

    def test_get_report_summary_with_statuses(self, tmp_path):
        results_dir = tmp_path / "allure-results"
        results_dir.mkdir()

        samples = [
            {"status": "passed"},
            {"status": "failed"},
            {"status": "failed"},
            {"status": "broken"},
            {"status": "skipped"},
        ]

        for index, payload in enumerate(samples, start=1):
            (results_dir / f"{index}-result.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

        reporter = AllureReporter(
            results_dir=str(results_dir),
            report_dir=str(tmp_path / "allure-report"),
        )

        assert reporter.get_report_summary() == {
            "total": 5,
            "passed": 1,
            "failed": 2,
            "broken": 1,
            "skipped": 1,
        }

    def test_write_fallback_results(self, tmp_path):
        reporter = AllureReporter(
            results_dir=str(tmp_path / "allure-results"),
            report_dir=str(tmp_path / "allure-report"),
        )

        created = reporter.write_fallback_results(
            test_cases=[
                {"id": "TC_001", "title": "login succeeds"},
                {"id": "TC_002", "title": "login fails"},
            ],
            error_message="spawn EPERM",
            script_path="midscene_run/generated/demo.spec.ts",
        )

        assert created == {
            "created": 2,
            "failed": 2,
            "passed": 0,
            "broken": 0,
            "skipped": 0,
            "total": 2,
        }
        assert reporter.get_report_summary()["failed"] == 2

    def test_write_results_from_execution(self, tmp_path):
        reporter = AllureReporter(
            results_dir=str(tmp_path / "allure-results"),
            report_dir=str(tmp_path / "allure-report"),
        )
        screenshot_path = tmp_path / "final-passed.png"
        screenshot_path.write_bytes(b"png-bytes")

        created = reporter.write_results_from_execution(
            execution_results={
                "tests": [
                    {
                        "name": "TC_001: success",
                        "status": "expected",
                        "duration": 1200,
                        "attachments": [
                            {
                                "name": "final-screenshot-passed",
                                "contentType": "image/png",
                                "path": str(screenshot_path),
                            }
                        ],
                    },
                    {"name": "TC_002: failure", "status": "unexpected", "duration": 2400},
                    {"name": "TC_003: skip", "status": "skipped", "duration": 0},
                ],
                "error": "Run-level error that should only be used as fallback",
                "metadata": {
                    "scenario_type": "login_only",
                    "success_signal": {"value": "LianLian"},
                    "manual_wait": True,
                },
            },
            script_path="midscene_run/generated/demo.spec.ts",
        )

        result_files = list((tmp_path / "allure-results").glob("*result*.json"))
        payloads = {
            payload["name"]: payload
            for payload in (
                json.loads(path.read_text(encoding="utf-8")) for path in result_files
            )
        }

        assert created == {
            "created": 3,
            "passed": 1,
            "failed": 1,
            "broken": 0,
            "skipped": 1,
            "total": 3,
        }
        assert reporter.get_report_summary() == {
            "total": 3,
            "passed": 1,
            "failed": 1,
            "broken": 0,
            "skipped": 1,
        }
        assert (tmp_path / "allure-results" / "environment.properties").exists()
        assert payloads["TC_001: success"]["steps"][0]["name"] == "Imported from Playwright JSON execution result"
        assert any(
            step["name"] == "Scenario type: login_only"
            for step in payloads["TC_001: success"]["steps"]
        )
        assert payloads["TC_001: success"]["attachments"][0]["name"] == "final-screenshot-passed"
        assert payloads["TC_001: success"]["attachments"][0]["type"] == "image/png"
        assert (tmp_path / "allure-results" / payloads["TC_001: success"]["attachments"][0]["source"]).exists()
        assert any(
            label["name"] == "tag" and label["value"] == "login_only"
            for label in payloads["TC_001: success"]["labels"]
        )
        assert payloads["TC_001: success"]["status"] == "passed"
        assert "statusDetails" not in payloads["TC_001: success"]
        assert payloads["TC_002: failure"]["status"] == "failed"
        assert (
            payloads["TC_002: failure"]["statusDetails"]["message"]
            == "Run-level error that should only be used as fallback"
        )

    def test_check_allure_installed(self):
        reporter = AllureReporter()
        assert isinstance(reporter.check_allure_installed(), bool)


class TestGenerateAllureReport:
    def test_generate_allure_report_no_results(self):
        result = generate_allure_report(results_dir="nonexistent-results")
        assert result["status"] == "error"
