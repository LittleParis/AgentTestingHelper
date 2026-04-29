"""Focused regression tests for stable Midscene generator behaviors."""

from unittest.mock import MagicMock, patch

from core.automation.midscene_generator import (
    ActionConversionResult,
    MidsceneScriptGenerator,
)


SAME_PAGE_FALLBACK = "\u9875\u9762\u4ecd\u505c\u7559\u5728\u5f53\u524dURL"
BLANK_INPUT_FALLBACK = "\u8f93\u5165\u6846\u4fdd\u6301\u7a7a\u767d\u72b6\u6001"
NO_ERROR_FALLBACK = "\u9875\u9762\u6ca1\u6709\u9519\u8bef\u63d0\u793a"


def test_convert_steps_with_llm_preserves_structured_response_shape():
    with patch("core.automation.midscene_generator.get_llm_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.invoke_structured.return_value = ActionConversionResult(
            steps=[
                {
                    "action_prompt": 'Type "test keyword" into the search box',
                    "verify_prompt": "Search input stays visible",
                }
            ]
        )
        mock_get_client.return_value = mock_client

        generator = MidsceneScriptGenerator(use_llm=True)
        _ = generator.llm_client

        result = generator._convert_steps_with_llm(
            [
                {
                    "action": 'Type "test keyword" into the search input',
                    "data": "test keyword",
                    "expected": "Search input stays visible",
                }
            ]
        )

    assert result[0]["action_prompt"] == 'Type "test keyword" into the search box'
    assert result[0]["verify_prompt"] == "Search input stays visible"
    assert result[0]["data"] == "test keyword"


def test_url_verification_uses_native_assertion():
    generator = MidsceneScriptGenerator(use_llm=False)
    joined = "\n".join(generator._generate_verify_lines("The page URL changes and includes the search query"))

    assert "expect.poll" in joined
    assert "page.url()" in joined


def test_generated_fixture_uses_visible_search_locators():
    generator = MidsceneScriptGenerator(use_llm=False)
    script = generator._generate_script_content(
        [
            {
                "id": "TC_001",
                "title": "Example",
                "priority": "high",
                "steps": [
                    {
                        "action": "Type a keyword into the search input",
                        "data": "test product",
                        "expected": "The input shows the typed keyword",
                    }
                ],
                "expected": "Input succeeds",
                "tags": [],
            }
        ],
        "https://www.baidu.com",
    )

    assert '#kw:visible' in script
    assert 'input:visible, textarea:visible' in script
    assert '#su:visible' in script


def test_negative_login_expectations_use_non_redirect_fallbacks():
    generator = MidsceneScriptGenerator(use_llm=False)

    assert generator._convert_expected_fallback(
        "The page stays on the current URL and does not navigate away"
    ) == SAME_PAGE_FALLBACK
    assert generator._convert_expected_fallback(
        "The username input remains empty"
    ) == BLANK_INPUT_FALLBACK


def test_no_error_expectation_maps_to_error_free_prompt():
    generator = MidsceneScriptGenerator(use_llm=False)

    assert generator._convert_expected_fallback("No error message appears") == NO_ERROR_FALLBACK
