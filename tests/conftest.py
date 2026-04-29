"""Shared pytest fixtures and lightweight runtime hygiene."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from core.utils.project_paths import GENERATED_TESTS_DIR, OUTPUT_DIR

try:  # pragma: no cover - environment-dependent import
    from playwright.async_api import async_playwright
except ModuleNotFoundError:  # pragma: no cover - environment-dependent import
    async_playwright = None


TIMESTAMP_PATTERN = re.compile(r"\(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\)")


def extract_timestamp(filename: str) -> tuple[str, str | None]:
    match = TIMESTAMP_PATTERN.search(filename)
    if match:
        timestamp = match.group()
        base_name = TIMESTAMP_PATTERN.sub("", filename)
        return base_name, timestamp
    return filename, None


def clean_old_files(directory: Path, keep_latest: int = 1) -> None:
    if not directory.exists():
        return

    grouped: dict[str, list[tuple[Path, str | None]]] = {}
    for file in directory.iterdir():
        if not file.is_file():
            continue
        base_name, timestamp = extract_timestamp(file.name)
        grouped.setdefault(base_name, []).append((file, timestamp))

    for files in grouped.values():
        with_timestamp = [(file, stamp) for file, stamp in files if stamp is not None]
        without_timestamp = [(file, stamp) for file, stamp in files if stamp is None]

        with_timestamp.sort(key=lambda item: item[1] or "", reverse=True)
        for file, _ in without_timestamp:
            file.unlink(missing_ok=True)
        for file, _ in with_timestamp[keep_latest:]:
            file.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def clean_output():
    clean_old_files(OUTPUT_DIR, keep_latest=1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield OUTPUT_DIR


@pytest.fixture(scope="session")
def clean_generated_tests():
    clean_old_files(GENERATED_TESTS_DIR, keep_latest=1)
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)
    yield GENERATED_TESTS_DIR


@pytest.fixture(scope="session")
def clean_all(clean_output, clean_generated_tests):
    yield {"output": clean_output, "generated_tests": clean_generated_tests}


@pytest.fixture(scope="function")
def clean_output_function():
    clean_old_files(OUTPUT_DIR, keep_latest=1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield OUTPUT_DIR


@pytest.fixture(scope="function")
def clean_generated_tests_function():
    clean_old_files(GENERATED_TESTS_DIR, keep_latest=1)
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)
    yield GENERATED_TESTS_DIR


@pytest.fixture(scope="session")
async def browser():
    if async_playwright is None:
        pytest.skip("playwright is not installed in this environment")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await page.close()
    await context.close()


def pytest_addoption(parser):
    parser.addoption("--clean-before", action="store_true", default=False, help="Clean generated files before test collection.")


def pytest_configure(config):
    config.addinivalue_line("markers", "ui: marks tests that require Playwright or browser automation")
    config.addinivalue_line("markers", "smoke: marks fast smoke tests")
    config.addinivalue_line("markers", "benchmark: marks stable benchmark/contract tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--clean-before"):
        clean_old_files(OUTPUT_DIR, keep_latest=1)
        clean_old_files(GENERATED_TESTS_DIR, keep_latest=1)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    if async_playwright is None:
        skip_ui = pytest.mark.skip(reason="playwright is not installed in this environment")
        for item in items:
            if "ui" in item.keywords or "browser" in item.fixturenames or "page" in item.fixturenames:
                item.add_marker(skip_ui)
