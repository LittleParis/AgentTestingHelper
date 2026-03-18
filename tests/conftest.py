"""Pytest配置和fixtures"""
import pytest
from playwright.async_api import async_playwright


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
