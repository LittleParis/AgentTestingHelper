"""测试执行器 - 执行 Midscene/Playwright 测试脚本"""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

# 清除代理设置（解决连接问题）
for _var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(_var, None)
os.environ['NO_PROXY'] = '*'


class TestExecutor:
    """
    测试执行器 - 执行 Midscene 生成的测试脚本

    支持执行 Playwright 测试脚本并收集执行结果。
    """

    # 默认配置
    DEFAULT_CONFIG = {
        # 浏览器配置
        "browser": "chromium",
        "headed": False,  # 无头模式
        "timeout": 120000,  # 120秒超时（Midscene AI 需要更长时间）

        # 执行配置
        "retries": 0,  # 失败重试次数
        "workers": 1,  # 并行worker数

        # 截图配置
        "screenshot_on_failure": True,
        "screenshot_on_success": False,

        # 报告配置
        "reporter": "list",  # list/html/json
        "output_dir": "test-results",

        # 浏览器路径
        "browsers_path": None,  # 默认使用环境变量
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化执行器

        Args:
            config: 配置选项，覆盖默认配置
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._last_results: Optional[Dict] = None

    def run_tests(self, script_path: str) -> Dict:
        """
        执行测试脚本

        Args:
            script_path: 测试脚本路径或目录

        Returns:
            执行结果字典:
            {
                "status": "success" | "error",
                "total": 10,
                "passed": 8,
                "failed": 2,
                "skipped": 0,
                "duration": 45.2,
                "tests": [...],
                "error": None | "错误信息"
            }
        """
        abs_path = str(Path(script_path).absolute())
        if not os.path.exists(abs_path):
            return {
                "status": "error",
                "error": f"Script path not found: {script_path}",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0,
                "tests": []
            }

        start_time = time.time()
        json_report_path = None

        try:
            env = os.environ.copy()
            if self.config.get("browsers_path"):
                env["PLAYWRIGHT_BROWSERS_PATH"] = self.config["browsers_path"]

            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                env.pop(var, None)
            env['NO_PROXY'] = '*'

            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
                json_report_path = f.name

            cmd_list = self._build_playwright_command_args(script_path, json_report_path)
            print(f"  [DEBUG] 执行命令: {' '.join(cmd_list)}")

            result = subprocess.run(
                cmd_list,
                capture_output=True,
                timeout=self._calculate_timeout(),
                shell=False,
                encoding='utf-8',
                errors='replace'
            )

            duration = time.time() - start_time
            print(f"  [DEBUG] 执行耗时: {duration:.2f}秒")
            print(f"  [DEBUG] returncode: {result.returncode}")

            if json_report_path and os.path.exists(json_report_path):
                parsed = self._parse_json_report(json_report_path)
            else:
                combined_output = result.stdout + result.stderr
                parsed = self._parse_text_output_fallback(combined_output)

            parsed["duration"] = round(duration, 2)
            parsed["status"] = self._determine_execution_status(result.returncode, parsed)
            parsed["raw_output"] = result.stdout + result.stderr
            parsed["stdout"] = result.stdout
            parsed["stderr"] = result.stderr
            parsed["returncode"] = result.returncode

            print(f"  [DEBUG] 解析结果: total={parsed['total']}, passed={parsed['passed']}, failed={parsed['failed']}")

            self._last_results = parsed
            return parsed

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Test execution timeout",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": time.time() - start_time,
                "tests": []
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": time.time() - start_time,
                "tests": []
            }
        finally:
            if json_report_path and os.path.exists(json_report_path):
                try:
                    os.unlink(json_report_path)
                except OSError:
                    pass

    def run_single_test(self, script_path: str, test_name: str) -> Dict:
        """
        执行单个测试用例

        Args:
            script_path: 测试脚本路径
            test_name: 测试用例名称（grep 模式）

        Returns:
            单个测试的执行结果
        """
        # 使用 --grep 过滤特定测试
        config = {**self.config, "grep": test_name}
        executor = TestExecutor(config)
        return executor.run_tests(script_path)

    def _parse_json_report(self, json_path: str) -> Dict:
        """
        解析 Playwright JSON 报告

        Args:
            json_path: JSON 报告文件路径

        Returns:
            解析后的结果字典
        """
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": []
        }

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

            stats = report.get("stats", {})
            results["passed"] = stats.get("expected", 0)
            results["failed"] = stats.get("unexpected", 0) + stats.get("flaky", 0)
            results["skipped"] = stats.get("skipped", 0)
            results["total"] = results["passed"] + results["failed"] + results["skipped"]

            for suite in report.get("suites", []):
                self._extract_tests_from_suite(suite, results["tests"])

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"  [DEBUG] JSON 解析失败: {e}")

        return results

    def _extract_tests_from_suite(self, suite: Dict, tests_list: List) -> None:
        """递归提取测试用例信息"""
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                test_name = test.get("title", spec.get("title", "unknown"))
                status = test.get("status", "unknown")
                duration = test.get("duration", 0)

                tests_list.append({
                    "name": test_name,
                    "status": status,
                    "duration": duration
                })

        for child_suite in suite.get("suites", []):
            self._extract_tests_from_suite(child_suite, tests_list)

    def _parse_text_output_fallback(self, output: str) -> Dict:
        """
        降级方案：解析 Playwright 文本输出
        仅在 JSON 报告不可用时使用
        """
        import re

        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": []
        }

        summary_passed = re.search(r"(\d+)\s+passed", output)
        summary_failed = re.search(r"(\d+)\s+failed", output)
        summary_skipped = re.search(r"(\d+)\s+skipped", output)

        if summary_passed or summary_failed:
            results["passed"] = int(summary_passed.group(1)) if summary_passed else 0
            results["failed"] = int(summary_failed.group(1)) if summary_failed else 0
            results["skipped"] = int(summary_skipped.group(1)) if summary_skipped else 0

        results["total"] = results["passed"] + results["failed"] + results["skipped"]

        return results

    def get_execution_summary(self) -> Dict:
        """
        获取最近一次执行的摘要

        Returns:
            执行摘要字典
        """
        if not self._last_results:
            return {
                "status": "no_results",
                "message": "No test execution results available"
            }

        return {
            "status": self._last_results.get("status"),
            "total": self._last_results.get("total", 0),
            "passed": self._last_results.get("passed", 0),
            "failed": self._last_results.get("failed", 0),
            "skipped": self._last_results.get("skipped", 0),
            "duration": self._last_results.get("duration", 0),
            "pass_rate": self._calculate_pass_rate()
        }

    def get_failed_tests(self) -> List[Dict]:
        """获取失败的测试列表"""
        if not self._last_results:
            return []
        return [t for t in self._last_results.get("tests", []) if t["status"] == "failed"]

    def get_screenshots(self) -> List[str]:
        """获取截图文件列表"""
        output_dir = Path(self.config["output_dir"])
        if not output_dir.exists():
            return []

        screenshots = []
        for pattern in ["**/*.png", "**/*.jpg"]:
            screenshots.extend(str(p) for p in output_dir.glob(pattern))

        return screenshots

    def _build_playwright_command(self, script_path: str) -> str:
        """
        构建 Playwright 执行命令

        Args:
            script_path: 测试脚本路径

        Returns:
            命令字符串
        """
        normalized_script_path = Path(script_path).as_posix()
        parts = [
            "npx playwright test",
            f'"{normalized_script_path}"',
            f"--timeout={self.config['timeout']}",
            f"--retries={self.config['retries']}",
        ]

        if self.config.get("headed"):
            parts.append("--headed")

        if self.config.get("project"):
            parts.append(f"--project={self.config['project']}")

        if self.config.get("grep"):
            parts.append(f'--grep "{self.config["grep"]}"')

        if self.config.get("workers", 1) > 1:
            parts.append(f"--workers={self.config['workers']}")

        return " ".join(parts)

    def _build_playwright_command_args(self, script_path: str, json_report_path: str) -> List[str]:
        """构建 subprocess 可直接执行的命令参数列表。"""
        npx_executable = self._resolve_npx_executable()
        normalized_script_path = Path(script_path).as_posix()

        # 获取项目根目录，用于定位配置文件
        project_root = self._get_project_root()
        config_path = Path(project_root) / "config" / "playwright.config.ts"

        parts = [
            npx_executable,
            "playwright",
            "test",
            normalized_script_path,
            f"--config={config_path.as_posix()}",
            f"--timeout={self.config['timeout']}",
            f"--retries={self.config['retries']}",
            f"--reporter=json",
            f"--output={json_report_path}",
        ]

        if self.config.get("headed"):
            parts.append("--headed")

        if self.config.get("project"):
            parts.append(f"--project={self.config['project']}")

        if self.config.get("grep"):
            parts.extend(["--grep", self.config["grep"]])

        if self.config.get("workers", 1) > 1:
            parts.append(f"--workers={self.config['workers']}")

        return parts

    def _calculate_timeout(self) -> int:
        """计算命令超时时间（秒）"""
        # 测试超时 + 额外缓冲时间
        test_timeout = self.config.get("timeout", 60000) / 1000
        buffer = 120  # 2分钟缓冲
        return int(test_timeout + buffer)

    def _get_project_root(self) -> str:
        """获取项目根目录"""
        # 当前文件: automation/test_executor.py
        # 项目根目录: 上两级，使用绝对路径
        return str(Path(__file__).parent.parent.absolute())

    def _calculate_pass_rate(self) -> float:
        """计算通过率"""
        if not self._last_results:
            return 0.0

        total = self._last_results.get("total", 0)
        if total == 0:
            return 0.0

        passed = self._last_results.get("passed", 0)
        return round(passed / total * 100, 2)

    def _determine_execution_status(self, returncode: int, parsed: Dict) -> str:
        """根据 Playwright 返回码和解析结果判断执行状态。"""
        if parsed.get("failed", 0) > 0:
            return "failed"

        if returncode != 0 and parsed.get("total", 0) == 0:
            return "error"

        if returncode != 0:
            return "failed"

        return "success"

    def _resolve_npx_executable(self) -> str:
        """在 Windows 下优先使用 npx.cmd，避免 shell=False 时找不到命令。"""
        return (
            shutil.which("npx.cmd")
            or shutil.which("npx")
            or "npx.cmd"
        )
