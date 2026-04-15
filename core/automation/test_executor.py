"""测试执行器 - 执行 Midscene/Playwright 测试脚本"""
import os
import re
import shutil
import subprocess
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
        # 保持相对路径（避免中文路径问题）
        # 但验证文件是否存在
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

        # 构建并执行命令
        cmd = self._build_playwright_command(script_path)
        start_time = time.time()

        # 调试：打印执行的命令
        print(f"  [DEBUG] 执行命令: {cmd}")

        try:
            # 设置环境变量
            env = os.environ.copy()
            if self.config.get("browsers_path"):
                env["PLAYWRIGHT_BROWSERS_PATH"] = self.config["browsers_path"]

            # 清除代理设置（解决连接问题）
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                env.pop(var, None)
            env['NO_PROXY'] = '*'

            # 执行 Playwright
            # 使用 shell=False 和列表参数，更可靠
            # 让 Playwright 自己加载 .env 文件
            cmd_list = self._build_playwright_command_args(script_path)
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                timeout=self._calculate_timeout(),
                shell=False,
                encoding='utf-8',
                errors='replace'  # 忽略编码错误
            )

            # 调试：将输出写入文件
            debug_file = Path("output") / "playwright_debug.txt"
            debug_file.parent.mkdir(exist_ok=True)
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"returncode: {result.returncode}\n")
                f.write(f"stdout length: {len(result.stdout)}\n")
                f.write(f"stderr length: {len(result.stderr)}\n")
                f.write(f"cwd: {os.getcwd()}\n")
                f.write(f"script exists: {os.path.exists(script_path)}\n")
                f.write("--- stdout ---\n")
                f.write(result.stdout)
                f.write("\n--- stderr ---\n")
                f.write(result.stderr)

            duration = time.time() - start_time

            # 调试：打印原始输出
            print(f"  [DEBUG] 执行耗时: {duration:.2f}秒")
            print(f"  [DEBUG] returncode: {result.returncode}")
            print(f"  [DEBUG] stdout长度: {len(result.stdout)}")

            # 解析输出
            combined_output = result.stdout + result.stderr
            parsed = self.parse_playwright_output(combined_output)
            parsed["duration"] = round(duration, 2)
            parsed["status"] = self._determine_execution_status(result.returncode, parsed)
            parsed["raw_output"] = combined_output
            parsed["stdout"] = result.stdout
            parsed["stderr"] = result.stderr
            parsed["returncode"] = result.returncode

            # 调试：打印解析结果
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

    def parse_playwright_output(self, output: str) -> Dict:
        """
        解析 Playwright 执行输出

        Args:
            output: Playwright CLI 输出

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

        # 已匹配的测试名称，避免重复
        matched_tests = set()

        # 匹配失败的测试: x  1 [chromium] › file:line:col › suite › test_name (duration)
        # 注意：x 后面有空格和数字，这是 Playwright 的格式
        failed_pattern = r"(?:x|✘)\s+\d*\s*\[.*?\].*›\s*(.+?)\s*\((\d+\.?\d*)\s*(?:ms|s)?\)"
        for match in re.finditer(failed_pattern, output):
            test_name = match.group(1).strip()
            duration = float(match.group(2))
            if test_name not in matched_tests:
                results["tests"].append({
                    "name": test_name,
                    "status": "failed",
                    "duration": duration
                })
                matched_tests.add(test_name)
                results["failed"] += 1

        # 匹配通过的测试: ✓ 或 ok
        # 格式1: ✓  [chromium] › file:line:col › suite › test_name (duration)
        # 格式2: ok  8 [chromium] › file:line:col › suite › test_name (duration)
        passed_pattern = r"(?:✓|ok)\s+\d*\s*\[.*?\].*›\s*(.+?)\s*\((\d+\.?\d*)\s*(?:ms|s)?\)"
        for match in re.finditer(passed_pattern, output):
            test_name = match.group(1).strip()
            duration = float(match.group(2))
            if test_name not in matched_tests:
                results["tests"].append({
                    "name": test_name,
                    "status": "passed",
                    "duration": duration
                })
                matched_tests.add(test_name)
                results["passed"] += 1

        # 匹配跳过的测试: -  [chromium] › file:line:col › test_name
        skipped_pattern = r"-\s+\[.*?\].*›\s*(.+?)(?:\s*\(\d+\.?\d*\s*(?:ms|s)?\))?"
        for match in re.finditer(skipped_pattern, output):
            test_name = match.group(1).strip()
            if test_name not in matched_tests:
                results["tests"].append({
                    "name": test_name,
                    "status": "skipped",
                    "duration": 0
                })
                matched_tests.add(test_name)
                results["skipped"] += 1

        # 匹配汇总信息（优先使用汇总数据）
        summary_passed = re.search(r"(\d+)\s+passed", output)
        summary_failed = re.search(r"(\d+)\s+failed", output)
        summary_skipped = re.search(r"(\d+)\s+skipped", output)

        if summary_passed or summary_failed:
            results["passed"] = int(summary_passed.group(1)) if summary_passed else 0
            results["failed"] = int(summary_failed.group(1)) if summary_failed else 0
            results["skipped"] = int(summary_skipped.group(1)) if summary_skipped else 0

        results["total"] = results["passed"] + results["failed"] + results["skipped"]

        return results

        # 匹配汇总信息
        # 格式: "2 passed (10.5s)" 或 "1 failed\n2 passed"
        summary_passed = re.search(r"(\d+)\s+passed", output)
        summary_failed = re.search(r"(\d+)\s+failed", output)
        summary_skipped = re.search(r"(\d+)\s+skipped", output)

        # 如果汇总信息存在，使用汇总数据（更准确）
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
            # 不覆盖 reporter，使用 playwright.config.ts 中的配置（包含 allure-playwright）
            f"--timeout={self.config['timeout']}",
            f"--retries={self.config['retries']}",
        ]

        # 有头模式
        if self.config.get("headed"):
            parts.append("--headed")

        # 项目配置
        if self.config.get("project"):
            parts.append(f"--project={self.config['project']}")

        # grep 过滤
        if self.config.get("grep"):
            parts.append(f'--grep "{self.config["grep"]}"')

        # workers
        if self.config.get("workers", 1) > 1:
            parts.append(f"--workers={self.config['workers']}")

        return " ".join(parts)

    def _build_playwright_command_args(self, script_path: str) -> List[str]:
        """构建 subprocess 可直接执行的命令参数列表。"""
        npx_executable = self._resolve_npx_executable()
        normalized_script_path = Path(script_path).as_posix()
        parts = [
            npx_executable,
            "playwright",
            "test",
            normalized_script_path,
            f"--timeout={self.config['timeout']}",
            f"--retries={self.config['retries']}",
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
