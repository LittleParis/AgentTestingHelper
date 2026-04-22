"""
单元测试：验证 MidsceneScriptGenerator 的 LLM 转换功能

测试目标：
1. 验证 LLM 批量转换步骤功能
2. 验证降级方案正常工作
3. 验证死代码已删除
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.automation.midscene_generator import (
    MidsceneScriptGenerator,
    ActionConversionResult
)


class TestMidsceneScriptGeneratorInit:
    """初始化测试"""

    def test_default_init(self):
        """测试默认初始化"""
        generator = MidsceneScriptGenerator()
        assert generator.use_llm is True
        assert generator._llm_client is None

    def test_init_with_use_llm_false(self):
        """测试禁用 LLM 模式"""
        generator = MidsceneScriptGenerator(use_llm=False)
        assert generator.use_llm is False


class TestFallbackConversion:
    """降级方案测试（不使用 LLM）"""

    def test_convert_action_with_data(self):
        """测试带数据的 action 转换"""
        generator = MidsceneScriptGenerator(use_llm=False)

        # 测试输入操作
        result = generator._convert_action_fallback("输入用户名", "admin")
        assert "admin" in result
        assert "输入" in result

    def test_convert_action_with_password(self):
        """测试密码输入转换"""
        generator = MidsceneScriptGenerator(use_llm=False)

        result = generator._convert_action_fallback("输入密码", "123456")
        assert "密码" in result
        assert "123456" in result

    def test_convert_action_click_login(self):
        """测试点击登录按钮转换"""
        generator = MidsceneScriptGenerator(use_llm=False)

        result = generator._convert_action_fallback("点击登录按钮", "")
        assert "登录" in result

    def test_convert_action_unknown(self):
        """测试未知操作返回默认值"""
        generator = MidsceneScriptGenerator(use_llm=False)

        result = generator._convert_action_fallback("未知操作xyz", "")
        assert result == "等待页面稳定"

    def test_convert_expected_success(self):
        """测试成功预期转换"""
        generator = MidsceneScriptGenerator(use_llm=False)

        result = generator._convert_expected_fallback("登录成功")
        assert "成功" in result

    def test_convert_expected_jump(self):
        """测试跳转预期转换"""
        generator = MidsceneScriptGenerator(use_llm=False)

        result = generator._convert_expected_fallback("跳转到首页")
        assert "URL" in result or "变化" in result

    def test_convert_expected_empty(self):
        """测试空预期返回空字符串"""
        generator = MidsceneScriptGenerator(use_llm=False)

        result = generator._convert_expected_fallback("")
        assert result == ""

        result = generator._convert_expected_fallback("N/A")
        assert result == ""


class TestLLMConversion:
    """LLM 转换测试"""

    def test_convert_steps_with_llm_success(self):
        """测试 LLM 成功转换步骤"""
        with patch('core.automation.midscene_generator.get_llm_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # Mock structured output
            mock_structured = MagicMock()
            mock_structured.invoke.return_value = ActionConversionResult(steps=[
                {"action_prompt": "在用户名输入框中输入 \"admin\"", "verify_prompt": ""},
                {"action_prompt": "点击登录按钮", "verify_prompt": "页面URL发生了变化"}
            ])
            mock_client.with_structured_output.return_value = mock_structured

            generator = MidsceneScriptGenerator(use_llm=True)
            # 触发 LLM 客户端初始化
            _ = generator.llm_client

            steps = [
                {"action": "输入用户名", "data": "admin", "expected": ""},
                {"action": "点击登录按钮", "data": "", "expected": "跳转"}
            ]

            result = generator._convert_steps_with_llm(steps)

            assert len(result) == 2
            assert result[0]["action_prompt"] == "在用户名输入框中输入 \"admin\""
            assert result[1]["verify_prompt"] == "页面URL发生了变化"

    def test_convert_steps_with_llm_fallback_on_error(self):
        """测试 LLM 失败时降级到关键词匹配"""
        with patch('core.automation.midscene_generator.get_llm_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # Mock structured output 抛出异常
            mock_structured = MagicMock()
            mock_structured.invoke.side_effect = Exception("LLM 调用失败")
            mock_client.with_structured_output.return_value = mock_structured

            generator = MidsceneScriptGenerator(use_llm=True)
            _ = generator.llm_client

            steps = [
                {"action": "输入用户名", "data": "admin", "expected": ""}
            ]

            result = generator._convert_steps_with_llm(steps)

            # 应该使用降级方案
            assert len(result) == 1
            assert "admin" in result[0]["action_prompt"]


class TestDeadCodeRemoved:
    """验证死代码已删除"""

    def test_generate_decorators_not_exists(self):
        """测试 _generate_decorators 方法已删除"""
        generator = MidsceneScriptGenerator()

        # 该方法不应该存在
        assert not hasattr(generator, '_generate_decorators')

    def test_convert_action_to_ai_prompt_not_exists(self):
        """测试旧方法 _convert_action_to_ai_prompt 已删除"""
        generator = MidsceneScriptGenerator()

        # 旧方法不应该存在
        assert not hasattr(generator, '_convert_action_to_ai_prompt')

    def test_convert_expected_to_ai_prompt_not_exists(self):
        """测试旧方法 _convert_expected_to_ai_prompt 已删除"""
        generator = MidsceneScriptGenerator()

        # 旧方法不应该存在
        assert not hasattr(generator, '_convert_expected_to_ai_prompt')


class TestScriptGeneration:
    """脚本生成测试"""

    def test_generate_script_without_llm(self):
        """测试不使用 LLM 生成脚本"""
        generator = MidsceneScriptGenerator(use_llm=False)

        test_cases = [
            {
                "id": "TC_001",
                "title": "测试登录",
                "priority": "high",
                "steps": [
                    {"action": "输入用户名", "data": "admin"},
                    {"action": "点击登录按钮", "data": ""}
                ],
                "expected": "登录成功",
                "tags": ["smoke"]
            }
        ]

        script = generator._generate_script_content(test_cases, "https://example.com/login")

        # 验证脚本内容
        assert "TC_001" in script
        assert "测试登录" in script
        assert "https://example.com/login" in script
        assert "await ai(" in script

    def test_generate_script_with_llm(self):
        """测试使用 LLM 生成脚本"""
        with patch('core.automation.midscene_generator.get_llm_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_structured = MagicMock()
            mock_structured.invoke.return_value = ActionConversionResult(steps=[
                {"action_prompt": "在用户名输入框中输入 \"admin\"", "verify_prompt": ""},
                {"action_prompt": "点击登录按钮", "verify_prompt": "页面跳转成功"}
            ])
            mock_client.with_structured_output.return_value = mock_structured

            generator = MidsceneScriptGenerator(use_llm=True)
            _ = generator.llm_client

            test_cases = [
                {
                    "id": "TC_002",
                    "title": "LLM 转换测试",
                    "priority": "medium",
                    "steps": [
                        {"action": "输入用户名", "data": "admin"},
                        {"action": "点击登录按钮", "data": ""}
                    ],
                    "expected": "登录成功",
                    "tags": []
                }
            ]

            script = generator._generate_script_content(test_cases, "https://example.com")

            assert "TC_002" in script
            assert "在用户名输入框中输入" in script


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
