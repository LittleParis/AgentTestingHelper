"""TestExecutor 单元测试 - Issue #9 修复验证"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.automation.test_executor import TestExecutor


class TestTestExecutorInit:
    """测试初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        executor = TestExecutor()
        assert executor.config["browser"] == "chromium"
        assert executor.config["headed"] is False
        assert executor.config["timeout"] == 120000
        assert executor._last_results is None

    def test_custom_config(self):
        """测试自定义配置"""
        executor = TestExecutor({"timeout": 60000, "headed": True})
        assert executor.config["timeout"] == 60000
        assert executor.config["headed"] is True


class TestParseJsonReport:
    """测试 JSON 报告解析"""

    def test_parse_valid_json_report(self):
        """测试解析有效的 JSON 报告"""
        executor = TestExecutor()

        report = {
            "stats": {
                "expected": 5,
                "unexpected": 2,
                "flaky": 1,
                "skipped": 1
            },
            "suites": [
                {
                    "specs": [
                        {
                            "title": "test spec",
                            "tests": [
                                {"title": "test1", "status": "passed", "duration": 100},
                                {"title": "test2", "status": "failed", "duration": 200}
                            ]
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(report, f)
            json_path = f.name

        try:
            result = executor._parse_json_report(json_path)
            assert result["passed"] == 5
            assert result["failed"] == 3  # unexpected + flaky
            assert result["skipped"] == 1
            assert result["total"] == 9
            assert len(result["tests"]) == 2
        finally:
            os.unlink(json_path)

    def test_parse_empty_json_report(self):
        """测试解析空 JSON 报告"""
        executor = TestExecutor()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            json_path = f.name

        try:
            result = executor._parse_json_report(json_path)
            assert result["passed"] == 0
            assert result["failed"] == 0
            assert result["total"] == 0
        finally:
            os.unlink(json_path)

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        executor = TestExecutor()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            json_path = f.name

        try:
            result = executor._parse_json_report(json_path)
            assert result["passed"] == 0
            assert result["failed"] == 0
        finally:
            os.unlink(json_path)


class TestExtractTestsFromSuite:
    """测试递归提取测试用例"""

    def test_extract_simple_suite(self):
        """测试提取简单套件"""
        executor = TestExecutor()
        tests_list = []

        suite = {
            "specs": [
                {
                    "title": "spec1",
                    "tests": [
                        {"title": "test1", "status": "passed", "duration": 100}
                    ]
                }
            ]
        }

        executor._extract_tests_from_suite(suite, tests_list)
        assert len(tests_list) == 1
        assert tests_list[0]["name"] == "test1"

    def test_extract_nested_suites(self):
        """测试提取嵌套套件"""
        executor = TestExecutor()
        tests_list = []

        suite = {
            "specs": [
                {
                    "title": "spec1",
                    "tests": [{"title": "test1", "status": "passed", "duration": 100}]
                }
            ],
            "suites": [
                {
                    "specs": [
                        {
                            "title": "spec2",
                            "tests": [{"title": "test2", "status": "failed", "duration": 200}]
                        }
                    ]
                }
            ]
        }

        executor._extract_tests_from_suite(suite, tests_list)
        assert len(tests_list) == 2


class TestParseTextOutputFallback:
    """测试文本输出降级解析"""

    def test_parse_summary_output(self):
        """测试解析汇总输出"""
        executor = TestExecutor()

        output = """
        Running tests...

          ✓  test1 (100ms)
          ✓  test2 (200ms)
          ✘  test3 (300ms)

        2 passed
        1 failed
        """

        result = executor._parse_text_output_fallback(output)
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["total"] == 3

    def test_parse_output_with_skipped(self):
        """测试解析包含跳过的输出"""
        executor = TestExecutor()

        output = "3 passed\n1 failed\n2 skipped"
        result = executor._parse_text_output_fallback(output)
        assert result["passed"] == 3
        assert result["failed"] == 1
        assert result["skipped"] == 2
        assert result["total"] == 6

    def test_parse_empty_output(self):
        """测试解析空输出"""
        executor = TestExecutor()
        result = executor._parse_text_output_fallback("")
        assert result["total"] == 0


class TestBuildPlaywrightCommand:
    """测试命令构建"""

    def test_build_basic_command(self):
        """测试构建基本命令"""
        executor = TestExecutor()
        cmd = executor._build_playwright_command("test.spec.ts")
        assert "npx playwright test" in cmd
        assert "test.spec.ts" in cmd
        assert "--timeout=120000" in cmd

    def test_build_command_with_headed(self):
        """测试构建有头模式命令"""
        executor = TestExecutor({"headed": True})
        cmd = executor._build_playwright_command("test.spec.ts")
        assert "--headed" in cmd

    def test_build_command_args_with_json_reporter(self):
        """测试构建包含 JSON reporter 的命令参数"""
        executor = TestExecutor()
        cmd_list = executor._build_playwright_command_args("test.spec.ts", "report.json")

        assert "playwright" in cmd_list
        assert "test" in cmd_list
        assert "--reporter=json" in cmd_list
        assert "--output=report.json" in cmd_list


class TestDeadCodeRemoved:
    """验证死代码已删除"""

    def test_parse_playwright_output_not_exists(self):
        """parse_playwright_output 方法已不存在（被新方法替代）"""
        executor = TestExecutor()
        assert not hasattr(executor, "parse_playwright_output")


class TestRunTests:
    """测试 run_tests 方法"""

    def test_run_tests_script_not_found(self):
        """测试脚本不存在时的处理"""
        executor = TestExecutor()
        result = executor.run_tests("nonexistent.spec.ts")

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
        assert result["total"] == 0

    @patch('core.automation.test_executor.subprocess.run')
    def test_run_tests_timeout(self, mock_run):
        """测试执行超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npx", timeout=60)

        with patch('os.path.exists', return_value=True):
            executor = TestExecutor()
            result = executor.run_tests("test.spec.ts")

        assert result["status"] == "error"
        assert "timeout" in result["error"].lower()
