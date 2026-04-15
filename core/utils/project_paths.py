"""项目运行时路径常量。"""
from pathlib import Path


OUTPUT_DIR = Path("output")
GENERATED_TESTS_DIR = Path("midscene_run/generated")
LEGACY_GENERATED_TESTS_DIR = Path("tests/generated")
ALLURE_RESULTS_DIR = Path("allure-results")
ALLURE_REPORT_DIR = Path("allure-report")
PLAYWRIGHT_RESULTS_DIR = Path("test-results")


def ensure_runtime_directories() -> None:
    """确保运行期需要的目录存在。"""
    for directory in [
        OUTPUT_DIR,
        GENERATED_TESTS_DIR,
        ALLURE_RESULTS_DIR,
        ALLURE_REPORT_DIR,
        PLAYWRIGHT_RESULTS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
