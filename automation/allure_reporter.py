"""Allure 报告生成器"""
import json
import os
import socket
import subprocess
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Optional


class AllureReporter:
    """
    Allure 报告生成器

    用于生成和管理 Allure 测试报告
    """

    def __init__(self, results_dir: str = "allure-results", report_dir: str = "allure-report"):
        """
        初始化报告生成器

        Args:
            results_dir: Allure 结果目录
            report_dir: Allure 报告目录
        """
        self.results_dir = Path(results_dir)
        self.report_dir = Path(report_dir)

    def generate_report(self, clean: bool = True, single_file: bool = True) -> dict:
        """
        生成 Allure 报告

        Args:
            clean: 是否清理旧的结果
            single_file: 是否生成单文件报告，便于直接用浏览器打开

        Returns:
            {
                "status": "success" | "error",
                "report_path": str,
                "error": Optional[str]
            }
        """
        # 检查结果目录是否存在
        if not self.results_dir.exists():
            return {
                "status": "error",
                "report_path": None,
                "error": f"结果目录不存在: {self.results_dir}"
            }

        # 检查是否有结果文件
        result_files = list(self.results_dir.glob("*"))
        if not result_files:
            return {
                "status": "error",
                "report_path": None,
                "error": "结果目录为空，没有测试结果"
            }

        try:
            # 清理旧报告
            if clean and self.report_dir.exists():
                shutil.rmtree(self.report_dir)

            # 生成报告
            cmd = f"allure generate {self.results_dir} -o {self.report_dir} --clean"
            if single_file:
                cmd += " --single-file"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "report_path": None,
                    "error": f"生成报告失败: {result.stderr}"
                }

            return {
                "status": "success",
                "report_path": str(self.report_dir.absolute()),
                "error": None,
                "summary": self.get_report_summary()
            }

        except Exception as e:
            return {
                "status": "error",
                "report_path": None,
                "error": str(e)
            }

    def open_report(self) -> dict:
        """
        打开已生成的 Allure 报告（启动本地 HTTP 服务）

        Returns:
            {
                "status": "success" | "error",
                "error": Optional[str]
            }
        """
        if not self.report_dir.exists():
            return {
                "status": "error",
                "error": f"报告目录不存在: {self.report_dir}"
            }

        try:
            host = "127.0.0.1"
            port = self._find_free_port()
            creationflags = 0
            if os.name == "nt":
                creationflags = (
                    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                    | getattr(subprocess, "DETACHED_PROCESS", 0)
                )
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "http.server",
                    str(port),
                    "--bind",
                    host,
                    "--directory",
                    str(self.report_dir),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                close_fds=True,
            )
            url = f"http://{host}:{port}"

            return {
                "status": "success",
                "error": None,
                "message": f"Allure 报告服务已启动，请在浏览器中查看: {url}",
                "url": url,
                "pid": process.pid,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _find_free_port(self) -> int:
        """获取一个可用的本地端口。"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def clean_results(self) -> None:
        """清理结果目录"""
        if self.results_dir.exists():
            shutil.rmtree(self.results_dir)
            print(f"已清理结果目录: {self.results_dir}")

    def write_fallback_results(
        self,
        test_cases: list[dict],
        error_message: str,
        script_path: Optional[str] = None,
    ) -> dict:
        """
        在测试框架未能正常产出 Allure 结果时，写入兜底失败结果。
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        now_ms = int(time.time() * 1000)
        package_name = Path(script_path).name if script_path else "generated.spec.ts"

        for index, test_case in enumerate(test_cases, start=1):
            test_name = f"{test_case.get('id', f'TC_{index:03d}')}: {test_case.get('title', '未命名测试')}"
            result = {
                "uuid": str(uuid.uuid4()),
                "name": test_name,
                "status": "failed",
                "statusDetails": {
                    "message": error_message,
                    "trace": error_message,
                },
                "stage": "finished",
                "steps": [],
                "attachments": [],
                "parameters": [],
                "labels": [
                    {"name": "language", "value": "javascript"},
                    {"name": "framework", "value": "playwright"},
                    {"name": "package", "value": package_name},
                    {"name": "suite", "value": package_name},
                ],
                "links": [],
                "start": now_ms + index,
                "stop": now_ms + index + 1,
                "fullName": f"{package_name}#{test_case.get('id', f'TC_{index:03d}')}",
                "titlePath": [package_name],
            }

            result_file = self.results_dir / f"{uuid.uuid4()}-result.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            created += 1

        return {
            "created": created,
            "failed": created,
            "passed": 0,
            "broken": 0,
            "skipped": 0,
            "total": created,
        }

    def get_report_summary(self) -> dict:
        """
        获取报告摘要

        Returns:
            {
                "total": int,
                "passed": int,
                "failed": int,
                "broken": int,
                "skipped": int
            }
        """
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "broken": 0,
            "skipped": 0
        }

        if not self.results_dir.exists():
            return summary

        for result_file in self.results_dir.glob("*result*.json"):
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    result = json.load(f)
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
        """检查 Allure 是否已安装"""
        try:
            result = subprocess.run(
                "allure --version",
                shell=True,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False


def generate_allure_report(results_dir: str = "allure-results", open_browser: bool = False) -> dict:
    """
    生成 Allure 报告的便捷函数

    Args:
        results_dir: 结果目录
        open_browser: 是否打开浏览器查看报告

    Returns:
        报告生成结果
    """
    reporter = AllureReporter(results_dir=results_dir)

    # 检查 Allure 是否安装
    if not reporter.check_allure_installed():
        return {
            "status": "error",
            "error": "Allure 未安装，请先安装: npm install -g allure-commandline"
        }

    # 生成报告
    result = reporter.generate_report()

    if result["status"] == "success" and open_browser:
        reporter.open_report()

    return result
