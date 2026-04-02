"""Pytest配置和fixtures"""
import os
import shutil
import pytest
from pathlib import Path
from playwright.async_api import async_playwright


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 需要清理的目录
OUTPUT_DIR = PROJECT_ROOT / "output"
GENERATED_TESTS_DIR = PROJECT_ROOT / "tests" / "generated"


@pytest.fixture(scope="session")
def clean_output():
    """
    清理 output 目录的 fixture

    使用方式:
        # 在测试前清理
        @pytest.mark.usefixtures("clean_output")
        def test_something(clean_output):
            ...

        # 或者直接作为参数
        def test_something(clean_output):
            # clean_output 是清理后的 output 目录路径
            pass
    """
    # 测试前清理
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.glob("*"):
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yield OUTPUT_DIR

    # 测试后可选择是否清理（默认保留结果）
    # 如需测试后清理，取消下面的注释
    # if OUTPUT_DIR.exists():
    #     shutil.rmtree(OUTPUT_DIR)


@pytest.fixture(scope="session")
def clean_generated_tests():
    """
    清理 tests/generated 目录的 fixture

    使用方式:
        def test_something(clean_generated_tests):
            # clean_generated_tests 是清理后的目录路径
            pass
    """
    # 测试前清理
    if GENERATED_TESTS_DIR.exists():
        for file in GENERATED_TESTS_DIR.glob("*.py"):
            file.unlink()
    else:
        GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    yield GENERATED_TESTS_DIR

    # 测试后可选择是否清理
    # if GENERATED_TESTS_DIR.exists():
    #     shutil.rmtree(GENERATED_TESTS_DIR)


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

    每个测试函数前后都会清理，确保测试隔离
    """
    # 测试前清理
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.glob("*"):
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yield OUTPUT_DIR

    # 测试后清理
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.glob("*"):
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)


@pytest.fixture(scope="function")
def clean_generated_tests_function():
    """
    函数级别的 tests/generated 清理 fixture

    每个测试函数前后都会清理
    """
    # 测试前清理
    if GENERATED_TESTS_DIR.exists():
        for file in GENERATED_TESTS_DIR.glob("*.py"):
            file.unlink()
    else:
        GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    yield GENERATED_TESTS_DIR

    # 测试后清理
    if GENERATED_TESTS_DIR.exists():
        for file in GENERATED_TESTS_DIR.glob("*.py"):
            file.unlink()


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
        # 清理所有生成的文件
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if GENERATED_TESTS_DIR.exists():
            for file in GENERATED_TESTS_DIR.glob("*.py"):
                file.unlink()
