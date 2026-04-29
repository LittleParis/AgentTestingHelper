from unittest.mock import MagicMock, patch

from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.requirement import RequirementAnalysisResult


VALID_REQUIREMENT_TEXT = """
# 登录需求

## Goal
用户可以成功登录系统并进入首页。

## Acceptance Criteria
1. 输入正确账号密码可以成功登录
"""


def make_result() -> RequirementAnalysisResult:
    return RequirementAnalysisResult.model_validate(
        {
            "requirements": [
                {
                    "id": "REQ_001",
                    "title": "登录成功",
                    "description": "用户输入正确账号密码后可以成功登录系统。",
                    "priority": "high",
                    "type": "functional",
                    "acceptance_criteria": ["输入正确账号密码可以成功登录"],
                    "ui_elements": ["用户名输入框", "密码输入框", "登录按钮"],
                }
            ],
            "summary": "识别出 1 个登录功能需求。",
            "total_count": 1,
        }
    )


def test_analyze_structured_uses_low_temperature_for_structured_call():
    mock_llm = MagicMock()
    mock_llm.invoke_structured.return_value = make_result()

    with patch("core.agents.requirement_analyzer.get_llm_client", return_value=mock_llm):
        analyzer = RequirementAnalyzer()
        result = analyzer.analyze_structured(VALID_REQUIREMENT_TEXT)

    assert result.total_count == 1
    mock_llm.invoke_structured.assert_called_once()
    _, kwargs = mock_llm.invoke_structured.call_args
    assert kwargs["operation"] == "requirement_analysis"
    assert kwargs["temperature"] == RequirementAnalyzer.ANALYSIS_TEMPERATURE


def test_fallback_invoke_uses_same_low_temperature():
    mock_llm = MagicMock()
    mock_llm.invoke_structured.side_effect = Exception("structured boom")
    mock_llm.chat_simple.return_value = """```json
{
  "requirements": [
    {
      "id": "REQ_001",
      "title": "登录成功",
      "description": "用户输入正确账号密码后可以成功登录系统。",
      "priority": "high",
      "type": "functional",
      "acceptance_criteria": ["输入正确账号密码可以成功登录"],
      "ui_elements": ["用户名输入框", "密码输入框", "登录按钮"]
    }
  ],
  "summary": "识别出 1 个登录功能需求。",
  "total_count": 1
}
```"""

    with patch("core.agents.requirement_analyzer.get_llm_client", return_value=mock_llm):
        analyzer = RequirementAnalyzer()
        result = analyzer.analyze_structured(VALID_REQUIREMENT_TEXT)

    assert result.total_count == 1
    mock_llm.chat_simple.assert_called_once()
    _, kwargs = mock_llm.chat_simple.call_args
    assert kwargs["temperature"] == RequirementAnalyzer.ANALYSIS_TEMPERATURE
    assert kwargs["max_tokens"] == 4096
