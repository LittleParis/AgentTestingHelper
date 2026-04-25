#!/usr/bin/env python3
"""Offline helper for rebuilding Allure result files from saved execution JSON.

This script is intentionally a debug/recovery tool. The normal workflow should
materialize Allure results inside the core pipeline before report generation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.automation.allure_reporter import AllureReporter


def _latest_execution_file(output_dir: Path) -> Path | None:
    execution_files = list(output_dir.glob("execution*.json"))
    if not execution_files:
        return None
    return max(execution_files, key=lambda path: path.stat().st_mtime)


def main() -> int:
    output_dir = Path("output")
    execution_file = _latest_execution_file(output_dir)
    if execution_file is None:
        print("No execution result file found under output/.")
        return 1

    reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")
    reporter.results_dir.mkdir(parents=True, exist_ok=True)

    for stale_file in reporter.results_dir.glob("*"):
        if stale_file.is_file():
            stale_file.unlink()

    execution_results = json.loads(execution_file.read_text(encoding="utf-8"))
    created = reporter.write_results_from_execution(execution_results=execution_results)

    if created["created"] <= 0:
        print(f"No test results found in {execution_file.name}.")
        return 1

    print(f"Rebuilt {created['created']} Allure result files from {execution_file.name}.")
    print(
        "Summary: "
        f"passed={created['passed']} failed={created['failed']} "
        f"broken={created['broken']} skipped={created['skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
