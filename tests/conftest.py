"""Pytest配置和fixtures"""
import os
import re
import shutil
import pytest
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 需要清理的目录
OUTPUT_DIR = PROJECT_ROOT / "output"
GENERATED_TESTS_DIR = PROJECT_ROOT / "tests" / "generated"

# 时间戳正则模式: (2026-04-03_12-30-45)
TIMESTAMP_PATTERN = re.compile(r"\(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\)")


def extract_timestamp(filename: str) -> tuple[str, str | None]:
    """
    从文件名提取基础名和时间戳

    Examples:
        "requirements(2026-04-03_12-30-45).json" -> ("requirements", "(2026-04-03_12-30-45)")
        "requirements.json" -> ("requirements", None)
        "tc_001(2026-04-03_12-30-45).py" -> ("tc_001", "(2026-04-03_12-30-45)")
    """
    match = TIMESTAMP_PATTERN.search(filename)
    if match:
        timestamp = match.group()
        base_name = TIMESTAMP_PATTERN.sub("", filename)
        return base_name, timestamp
    return filename, None


def clean_old_files(directory: Path, keep_latest: int = 1):
    """
    清理历史文件，只保留最新的 N 个版本

    Args:
        directory: 目标目录
        keep_latest: 保留最新版本数量，默认 1
    """
    if not directory.exists():
        return

    # 按基础名分组
    file_groups: dict[str, list[tuple[Path, str | None]]] = {}

    for file in directory.iterdir():
        if file.is_file():
            base_name, timestamp = extract_timestamp(file.name)
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append((file, timestamp))

    # 对每个分组，删除旧版本
    for base_name, files in file_groups.items():
        # 分离带时间戳和不带时间戳的文件
        with_timestamp = [(f, t) for f, t in files if t is not None]
        without_timestamp = [(f, t) for f, t in files if t is None]

        # 按时间戳排序（最新的在前）
        with_timestamp.sort(key=lambda x: x[1] or "", reverse=True)

        # 删除不带时间戳的旧文件
        for file, _ in without_timestamp:
            file.unlink()
            print(f"  [清理] 删除旧文件: {file.name}")

        # 删除超出保留数量的带时间戳文件
        for file, _ in with_timestamp[keep_latest:]:
            file.unlink()
            print(f"  [清理] 删除历史版本: {file.name}")


@pytest.fixture(scope="session")
def clean_output():
    """
    清理 output 目录的历史文件 fixture

    功能:
        - 删除不带时间戳的旧文件
        - 只保留最新版本的带时间戳文件

    使用方式:
        @pytest.mark.usefixtures("clean_output")
        def test_something(clean_output):
            ...
    """
    print("\n[Fixture] 清理 output 目录历史文件...")
    clean_old_files(OUTPUT_DIR, keep_latest=1)

    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yield OUTPUT_DIR


@pytest.fixture(scope="session")
def clean_generated_tests():
    """
    清理 tests/generated 目录的历史文件 fixture

    功能:
        - 删除不带时间戳的旧文件
        - 只保留最新版本的带时间戳文件
    """
    print("\n[Fixture] 清理 tests/generated 目录历史文件...")
    clean_old_files(GENERATED_TESTS_DIR, keep_latest=1)

    if not GENERATED_TESTS_DIR.exists():
        GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    yield GENERATED_TESTS_DIR


@pytest.fixture(scope="session")
def clean_all(clean_output, clean_generated_tests):
    """
    清理所有生成文件的 fixture

    同时清理:
    - output/
    - tests/generated/
    """
    yield {
        "output": clean_output,
        "generated_tests": clean_generated_tests
    }


@pytest.fixture(scope="function")
def clean_output_function():
    """
    函数级别的 output 清理 fixture

    每个测试函数前清理历史文件，确保测试隔离
    """
    print("\n[Fixture] 清理 output 目录历史文件 (function级)...")
    clean_old_files(OUTPUT_DIR, keep_latest=1)

    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yield OUTPUT_DIR


@pytest.fixture(scope="function")
def clean_generated_tests_function():
    """
    函数级别的 tests/generated 清理 fixture

    每个测试函数前清理历史文件
    """
    print("\n[Fixture] 清理 tests/generated 目录历史文件 (function级)...")
    clean_old_files(GENERATED_TESTS_DIR, keep_latest=1)

    if not GENERATED_TESTS_DIR.exists():
        GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    yield GENERATED_TESTS_DIR


# ============ 原有的 Playwright fixtures ============

@pytest.fixture(scope="session")
async def browser():
    """浏览器实例fixture"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """页面实例fixture"""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await page.close()
    await context.close()


# ============ 命令行选项 ============

def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--clean-before",
        action="store_true",
        default=False,
        help="测试前清理所有生成的文件"
    )
    parser.addoption(
        "--clean-after",
        action="store_true",
        default=False,
        help="测试后清理所有生成的文件"
    )
    parser.addoption(
        "--keep-output",
        action="store_true",
        default=False,
        help="保留 output 目录（不清理）"
    )


def pytest_configure(config):
    """pytest 配置钩子"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "clean_output: 清理 output 目录"
    )
    config.addinivalue_line(
        "markers", "clean_generated: 清理 tests/generated 目录"
    )
    config.addinivalue_line(
        "markers", "clean_all: 清理所有生成的文件"
    )


def pytest_collection_modifyitems(config, items):
    """根据命令行选项修改测试项"""
    clean_before = config.getoption("--clean-before")

    if clean_before:
        print("\n[pytest] 清理历史文件...")
        # 清理历史文件，保留最新版本
        clean_old_files(OUTPUT_DIR, keep_latest=1)
        clean_old_files(GENERATED_TESTS_DIR, keep_latest=1)

        # 确保目录存在
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)
