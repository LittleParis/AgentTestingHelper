"""Unit tests for TestExecutor."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.automation.test_executor import TestExecutor


class TestTestExecutorInit:
    def test_default_init(self):
        executor = TestExecutor()
        assert executor.config["browser"] == "chromium"
        assert executor.config["headed"] is False
        assert executor.config["timeout"] == 120000
        assert executor._last_results is None

    def test_custom_config(self):
        executor = TestExecutor({"timeout": 60000, "headed": True, "workers": 2})
        assert executor.config["timeout"] == 60000
        assert executor.config["headed"] is True
        assert executor.config["workers"] == 2


class TestParseJsonReport:
    def test_parse_valid_json_report(self):
        executor = TestExecutor()
        report = {
            "stats": {
                "expected": 5,
                "unexpected": 2,
                "flaky": 1,
                "skipped": 1,
            },
            "suites": [
                {
                    "specs": [
                        {
                            "title": "test spec",
                            "tests": [
                                {"title": "test1", "status": "passed", "duration": 100},
                                {"title": "test2", "status": "failed", "duration": 200},
                            ],
                        }
                    ]
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
            json.dump(report, file)
            json_path = file.name

        try:
            result = executor._parse_json_report(json_path)
        finally:
            os.unlink(json_path)

        assert result["passed"] == 5
        assert result["failed"] == 3
        assert result["skipped"] == 1
        assert result["total"] == 9
        assert len(result["tests"]) == 2

    def test_parse_json_report_text(self):
        executor = TestExecutor()
        report_text = json.dumps(
            {
                "stats": {"expected": 1, "unexpected": 1, "flaky": 0, "skipped": 1},
                "suites": [],
            }
        )

        result = executor._parse_json_report_text(report_text)

        assert result["passed"] == 1
        assert result["failed"] == 1
        assert result["skipped"] == 1
        assert result["total"] == 3

    def test_parse_invalid_json(self):
        executor = TestExecutor()
        result = executor._parse_json_report_text("not valid json")
        assert result["total"] == 0


class TestExtractTestsFromSuite:
    def test_extract_nested_suites(self):
        executor = TestExecutor()
        tests_list = []
        suite = {
            "specs": [
                {
                    "title": "spec1",
                    "tests": [{"title": "test1", "status": "passed", "duration": 100}],
                }
            ],
            "suites": [
                {
                    "specs": [
                        {
                            "title": "spec2",
                            "tests": [{"title": "test2", "status": "failed", "duration": 200}],
                        }
                    ]
                }
            ],
        }

        executor._extract_tests_from_suite(suite, tests_list)

        assert len(tests_list) == 2
        assert tests_list[0]["name"] == "test1"
        assert tests_list[1]["status"] == "failed"

    def test_extracts_test_level_error_details(self):
        executor = TestExecutor()
        tests_list = []
        suite = {
            "specs": [
                {
                    "title": "login spec",
                    "tests": [
                        {
                            "title": "login waits for manual verification",
                            "status": "unexpected",
                            "duration": 1234,
                            "results": [
                                {
                                    "errors": [
                                        {
                                            "message": "manual_verification_timeout",
                                            "stack": "manual_verification_timeout\n at login.spec.ts:10",
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        executor._extract_tests_from_suite(suite, tests_list)

        assert tests_list[0]["error"] == "manual_verification_timeout"
        assert "login.spec.ts" in tests_list[0]["trace"]

    def test_extracts_test_attachments(self):
        executor = TestExecutor()
        tests_list = []
        suite = {
            "specs": [
                {
                    "title": "login spec",
                    "tests": [
                        {
                            "title": "login captures final screenshot",
                            "status": "expected",
                            "duration": 1234,
                            "results": [
                                {
                                    "attachments": [
                                        {
                                            "name": "final-screenshot-passed",
                                            "contentType": "image/png",
                                            "path": "test-results/final-passed.png",
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        executor._extract_tests_from_suite(suite, tests_list)

        assert tests_list[0]["attachments"] == [
            {
                "name": "final-screenshot-passed",
                "contentType": "image/png",
                "path": "test-results/final-passed.png",
            }
        ]


class TestParseTextOutputFallback:
    def test_parse_summary_output(self):
        executor = TestExecutor()
        output = "2 passed\n1 failed\n3 skipped"

        result = executor._parse_text_output_fallback(output)

        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 3
        assert result["total"] == 6

    def test_parse_empty_output(self):
        executor = TestExecutor()
        result = executor._parse_text_output_fallback("")
        assert result["total"] == 0


class TestBuildPlaywrightCommand:
    def test_build_basic_command(self):
        executor = TestExecutor()
        cmd = executor._build_playwright_command("test.spec.ts")
        assert "npx playwright test" in cmd
        assert "test.spec.ts" in cmd
        assert "--timeout=120000" in cmd
        assert "--reporter=json" in cmd
        assert "--workers=1" in cmd

    def test_build_command_args_with_json_reporter(self):
        executor = TestExecutor()
        cmd_list = executor._build_playwright_command_args("test.spec.ts")

        assert "playwright" in cmd_list
        assert "test" in cmd_list
        assert "--reporter=json" in cmd_list
        assert "--workers=1" in cmd_list
        assert any(arg.startswith("--config=") for arg in cmd_list)

    def test_normalize_script_path_inside_project(self):
        executor = TestExecutor()
        project_root = executor._get_project_root()
        script_path = str(Path(project_root) / "midscene_run" / "generated" / "demo.spec.ts")

        normalized = executor._normalize_script_path(script_path, project_root)

        assert normalized == "midscene_run/generated/demo.spec.ts"


class TestExecutionHelpers:
    def test_parse_playwright_output_not_exists(self):
        executor = TestExecutor()
        assert not hasattr(executor, "parse_playwright_output")

    def test_determine_execution_status(self):
        executor = TestExecutor()
        assert executor._determine_execution_status(0, {"failed": 0, "total": 1}) == "success"
        assert executor._determine_execution_status(1, {"failed": 1, "total": 1}) == "failed"
        assert executor._determine_execution_status(1, {"failed": 0, "total": 0}) == "error"


class TestRunTests:
    def test_run_tests_script_not_found(self):
        executor = TestExecutor()
        result = executor.run_tests("nonexistent.spec.ts")

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
        assert result["total"] == 0

    @patch("core.automation.test_executor.subprocess.run")
    def test_run_tests_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npx", timeout=60)

        with patch("os.path.exists", return_value=True):
            executor = TestExecutor()
            result = executor.run_tests("test.spec.ts")

        assert result["status"] == "error"
        assert "timeout" in result["error"].lower()

    @patch("core.automation.test_executor.subprocess.run")
    def test_run_tests_falls_back_to_text_summary(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "2 failed\n1 passed"

        with patch("os.path.exists", return_value=True):
            executor = TestExecutor()
            result = executor.run_tests("test.spec.ts")

        assert result["status"] == "failed"
        assert result["passed"] == 1
        assert result["failed"] == 2

    @patch("core.automation.test_executor.subprocess.run")
    def test_run_tests_applies_env_overrides(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(
            {
                "stats": {"expected": 1, "unexpected": 0, "flaky": 0, "skipped": 0},
                "suites": [],
            }
        )
        mock_run.return_value.stderr = ""

        with patch("os.path.exists", return_value=True):
            executor = TestExecutor(
                {
                    "env_overrides": {
                        "LOGIN_USERNAME": "sample_user@example.com",
                        "LOGIN_PASSWORD": "sample-password-123",
                    }
                }
            )
            executor.run_tests("test.spec.ts")

        _, kwargs = mock_run.call_args
        assert kwargs["env"]["LOGIN_USERNAME"] == "sample_user@example.com"
        assert kwargs["env"]["LOGIN_PASSWORD"] == "sample-password-123"
