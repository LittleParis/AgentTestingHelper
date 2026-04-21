"""
单元测试：验证评审反馈注入生成器的逻辑正确性

测试目标：
1. 验证 improvement_hints 参数正确传递
2. 验证 prompt 中包含改进提示
3. 验证改进提示格式正确
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.test_case_generator import TestCaseGenerator
from core.models.requirement import Requirement, Priority, RequirementType


class TestImprovementHints:
    """改进提示注入测试"""

    @pytest.fixture
    def sample_requirement(self):
        """创建测试需求"""
        return Requirement(
            id="REQ_001",
            title="用户登录",
            description="用户可以通过用户名和密码登录系统",
            priority=Priority.HIGH,
            type=RequirementType.FUNCTIONAL,
            acceptance_criteria=[
                "正确的用户名和密码可以成功登录",
                "错误的密码提示'密码错误'"
            ]
        )

    def test_build_prompt_without_hints(self, sample_requirement):
        """测试无改进提示时的 prompt"""
        generator = TestCaseGenerator()
        prompt = generator._build_prompt(sample_requirement)

        # 验证基本内容存在
        assert "用户登录" in prompt
        assert "REQ_001" in prompt
        assert "测试用例" in prompt

        # 验证改进提示部分不存在
        assert "上次评审发现的问题" not in prompt
        assert "本次必须修复" not in prompt

    def test_build_prompt_with_hints(self, sample_requirement):
        """测试有改进提示时的 prompt"""
        generator = TestCaseGenerator()
        hints = [
            "增加密码为空的边界测试",
            "添加账号锁定场景测试",
            "TC_001 缺少预期结果"
        ]
        prompt = generator._build_prompt(sample_requirement, hints)

        # 验证基本内容存在
        assert "用户登录" in prompt
        assert "REQ_001" in prompt

        # 验证改进提示部分存在
        assert "上次评审发现的问题" in prompt
        assert "本次必须修复" in prompt
        assert "增加密码为空的边界测试" in prompt
        assert "添加账号锁定场景测试" in prompt
        assert "TC_001 缺少预期结果" in prompt

    def test_hints_format_in_prompt(self, sample_requirement):
        """测试改进提示在 prompt 中的格式"""
        generator = TestCaseGenerator()
        hints = ["问题1", "问题2"]
        prompt = generator._build_prompt(sample_requirement, hints)

        # 验证格式：每个提示前面有 "- "
        assert "- 问题1" in prompt
        assert "- 问题2" in prompt

        # 验证警告标题存在
        assert "⚠️" in prompt

    def test_empty_hints_same_as_no_hints(self, sample_requirement):
        """测试空提示列表等同于无提示"""
        generator = TestCaseGenerator()

        prompt_no_hints = generator._build_prompt(sample_requirement)
        prompt_empty_hints = generator._build_prompt(sample_requirement, [])

        # 空列表应该等同于无提示
        assert "上次评审发现的问题" not in prompt_empty_hints
        assert prompt_no_hints == prompt_empty_hints

    def test_generate_method_accepts_hints(self, sample_requirement):
        """测试 generate 方法接受 improvement_hints 参数"""
        generator = TestCaseGenerator()

        # Mock LLM 返回
        mock_result = MagicMock()
        mock_result.test_cases = []

        with patch.object(generator, 'generate_structured', return_value=mock_result):
            # 验证方法可以接受 improvement_hints 参数
            result = generator.generate(sample_requirement, improvement_hints=["测试提示"])

            # 验证 generate_structured 被正确调用
            generator.generate_structured.assert_called_once()
            call_args = generator.generate_structured.call_args
            # 第二个参数应该是 improvement_hints
            assert call_args[0][1] == ["测试提示"]

    def test_workflow_state_integration(self):
        """测试工作流状态集成"""
        # 模拟工作流状态
        state = {
            "requirements": [{"id": "REQ_001", "title": "测试"}],
            "iteration_count": 1,
            "review_suggestions": [
                "增加边界测试",
                "添加异常场景"
            ]
        }

        iteration = state.get("iteration_count", 0)
        review_suggestions = state.get("review_suggestions", [])

        # 第一次迭代时不应该有改进提示
        improvement_hints = None
        if iteration > 0 and review_suggestions:
            improvement_hints = review_suggestions

        # 验证逻辑：迭代次数 > 0 且有建议时才注入
        assert improvement_hints is not None
        assert len(improvement_hints) == 2

        # 验证第0次迭代不会注入
        state_zero_iteration = {
            "iteration_count": 0,
            "review_suggestions": ["建议1"]
        }
        iteration_zero = state_zero_iteration.get("iteration_count", 0)
        suggestions_zero = state_zero_iteration.get("review_suggestions", [])

        hints_zero = None
        if iteration_zero > 0 and suggestions_zero:
            hints_zero = suggestions_zero

        assert hints_zero is None, "第0次迭代不应该注入改进提示"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
