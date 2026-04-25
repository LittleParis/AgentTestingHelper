"""项目运行时路径常量。"""
from pathlib import Path

# 项目根目录（绝对路径）
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "output"
LLM_DIAGNOSTICS_DIR = OUTPUT_DIR / "llm_diagnostics"
GENERATED_TESTS_DIR = PROJECT_ROOT / "midscene_run" / "generated"
LEGACY_GENERATED_TESTS_DIR = PROJECT_ROOT / "tests" / "generated"

# Allure 报告目录
ALLURE_RESULTS_DIR = PROJECT_ROOT / "allure-results"
ALLURE_REPORT_DIR = PROJECT_ROOT / "allure-report"

# Playwright 测试结果
PLAYWRIGHT_RESULTS_DIR = PROJECT_ROOT / "test-results"


def ensure_runtime_directories() -> None:
    """确保运行期需要的目录存在。"""
    for directory in [
        OUTPUT_DIR,
        LLM_DIAGNOSTICS_DIR,
        GENERATED_TESTS_DIR,
        ALLURE_RESULTS_DIR,
        ALLURE_REPORT_DIR,
        PLAYWRIGHT_RESULTS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
