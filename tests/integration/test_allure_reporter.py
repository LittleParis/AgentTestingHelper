"""AllureReporter 单元测试"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.automation.allure_reporter import AllureReporter


class TestAllureReporter:
    """AllureReporter 测试类"""

    def test_init(self):
        """测试初始化"""
        reporter = AllureReporter()
        assert reporter.results_dir.name == "allure-results"
        assert reporter.report_dir.name == "allure-report"

    def test_init_custom_dirs(self):
        """测试自定义目录"""
        reporter = AllureReporter(
            results_dir="custom-results",
            report_dir="custom-report"
        )
        assert reporter.results_dir.name == "custom-results"
        assert reporter.report_dir.name == "custom-report"

    def test_generate_report_no_results(self):
        """测试结果目录不存在"""
        reporter = AllureReporter(
            results_dir="nonexistent-results",
            report_dir="test-report"
        )
        result = reporter.generate_report()

        assert result["status"] == "error"
        assert "不存在" in result["error"]

    def test_get_report_summary_empty(self):
        """测试空结果摘要"""
        reporter = AllureReporter(
            results_dir="nonexistent-results",
            report_dir="test-report"
        )
        summary = reporter.get_report_summary()

        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0

    def test_get_report_summary_with_statuses(self, tmp_path):
        """测试从 Allure 结果文件中统计状态"""
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
                encoding="utf-8"
            )

        reporter = AllureReporter(
            results_dir=str(results_dir),
            report_dir=str(tmp_path / "allure-report")
        )

        summary = reporter.get_report_summary()

        assert summary == {
            "total": 5,
            "passed": 1,
            "failed": 2,
            "broken": 1,
            "skipped": 1,
        }

    def test_write_fallback_results(self, tmp_path):
        """测试写入兜底失败结果"""
        reporter = AllureReporter(
            results_dir=str(tmp_path / "allure-results"),
            report_dir=str(tmp_path / "allure-report"),
        )

        created = reporter.write_fallback_results(
            test_cases=[
                {"id": "TC_001", "title": "登录成功"},
                {"id": "TC_002", "title": "登录失败"},
            ],
            error_message="spawn EPERM",
            script_path="midscene_run/generated/demo.spec.ts",
        )

        summary = reporter.get_report_summary()

        assert created["created"] == 2
        assert summary["failed"] == 2
        assert summary["total"] == 2

    def test_check_allure_installed(self):
        """测试 Allure 安装检查"""
        reporter = AllureReporter()
        # 这个测试取决于环境，只检查方法能正常调用
        result = reporter.check_allure_installed()
        assert isinstance(result, bool)


class TestGenerateAllureReport:
    """便捷函数测试"""

    def test_generate_allure_report_no_results(self):
        """测试无结果时的报告生成"""
        from core.automation.allure_reporter import generate_allure_report

        result = generate_allure_report(results_dir="nonexistent-results")

        # 可能是 Allure 未安装，也可能是结果不存在
        assert result["status"] == "error"
