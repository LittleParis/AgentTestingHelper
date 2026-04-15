"""
阶段2工作流测试

测试 Agent 协作功能：
- 需求分析节点
- 测试用例生成节点
- 评审节点
- 反馈循环
"""
import pytest
from unittest.mock import patch, MagicMock

from core.agents.workflow import (
    AgentState,
    analyze_requirements_node,
    generate_test_cases_node,
    review_test_cases_node,
    should_regenerate,
    increment_iteration,
    build_workflow,
    run_workflow
)


# ============ 测试数据 ============

SAMPLE_REQUIREMENT = """
# 用户登录功能

## 功能描述
用户可以通过用户名和密码登录系统。

## 验收标准
1. 正确的用户名和密码可以成功登录
2. 错误的密码提示"密码错误"
3. 用户名不存在提示"用户不存在"
"""

SAMPLE_REQUIREMENTS = [
    {
        "id": "REQ_001",
        "title": "用户登录",
        "description": "用户可以通过用户名和密码登录",
        "acceptance_criteria": [
            "正确的用户名和密码可以成功登录",
            "错误的密码提示错误信息"
        ]
    }
]

SAMPLE_TEST_CASES = [
    {
        "id": "TC_001",
        "title": "正确登录",
        "steps": ["输入用户名", "输入密码", "点击登录"],
        "expected": "登录成功"
    },
    {
        "id": "TC_002",
        "title": "密码错误",
        "steps": ["输入用户名", "输入错误密码", "点击登录"],
        "expected": "提示密码错误"
    }
]


# ============ 节点函数测试 ============

class TestAnalyzeRequirementsNode:
    """测试需求分析节点"""

    @patch("agents.workflow.RequirementAnalyzer")
    def test_analyze_success(self, mock_analyzer_class):
        """测试成功分析需求"""
        # Mock 返回值
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "requirements": SAMPLE_REQUIREMENTS,
            "summary": "登录功能需求"
        }
        mock_analyzer_class.return_value = mock_analyzer

        # 准备状态
        state: AgentState = {
            "requirement_text": SAMPLE_REQUIREMENT,
            "requirements": None,
            "requirement_summary": None,
            "test_cases": None,
            "review_passed": None,
            "review_comments": None,
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "init",
            "agent_messages": []
        }

        # 执行
        result = analyze_requirements_node(state)

        # 验证
        assert result["requirements"] == SAMPLE_REQUIREMENTS
        assert result["requirement_summary"] == "登录功能需求"
        assert result["current_step"] == "requirement_analyzed"
        assert len(result["agent_messages"]) == 1


class TestGenerateTestCasesNode:
    """测试用例生成节点"""

    @patch("agents.workflow.TestCaseGenerator")
    def test_generate_success(self, mock_generator_class):
        """测试成功生成测试用例"""
        # Mock 返回值
        mock_generator = MagicMock()
        mock_generator.generate.return_value = SAMPLE_TEST_CASES
        mock_generator_class.return_value = mock_generator

        # 准备状态
        state: AgentState = {
            "requirement_text": SAMPLE_REQUIREMENT,
            "requirements": SAMPLE_REQUIREMENTS,
            "requirement_summary": None,
            "test_cases": None,
            "review_passed": None,
            "review_comments": None,
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "requirement_analyzed",
            "agent_messages": []
        }

        # 执行
        result = generate_test_cases_node(state)

        # 验证
        assert len(result["test_cases"]) == 2
        assert result["current_step"] == "test_cases_generated"


class TestReviewTestCasesNode:
    """测试评审节点"""

    def test_review_passed(self):
        """测试评审通过"""
        state: AgentState = {
            "requirement_text": SAMPLE_REQUIREMENT,
            "requirements": SAMPLE_REQUIREMENTS,
            "requirement_summary": None,
            "test_cases": SAMPLE_TEST_CASES,
            "review_passed": None,
            "review_comments": None,
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "test_cases_generated",
            "agent_messages": []
        }

        result = review_test_cases_node(state)

        # 用例数量 >= 需求数量，应该通过
        assert result["review_passed"] == True
        assert result["current_step"] == "reviewed"

    def test_review_failed_missing_cases(self):
        """测试评审失败 - 用例数量不足"""
        state: AgentState = {
            "requirement_text": SAMPLE_REQUIREMENT,
            "requirements": SAMPLE_REQUIREMENTS + [
                {"id": "REQ_002", "title": "需求2"},
                {"id": "REQ_003", "title": "需求3"},
            ],
            "requirement_summary": None,
            "test_cases": SAMPLE_TEST_CASES,  # 只有2个用例，但有3个需求
            "review_passed": None,
            "review_comments": None,
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "test_cases_generated",
            "agent_messages": []
        }

        result = review_test_cases_node(state)

        # 用例数量 < 需求数量，应该失败
        assert result["review_passed"] == False
        assert len(result["review_comments"]) > 0


# ============ 路由函数测试 ============

class TestShouldRegenerate:
    """测试路由逻辑"""

    def test_should_end_when_passed(self):
        """评审通过时应该结束"""
        state: AgentState = {
            "requirement_text": "",
            "requirements": [],
            "requirement_summary": None,
            "test_cases": [],
            "review_passed": True,  # 通过
            "review_comments": [],
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "reviewed",
            "agent_messages": []
        }

        result = should_regenerate(state)
        assert result == "end"

    def test_should_regenerate_when_failed(self):
        """评审未通过时应该重新生成"""
        state: AgentState = {
            "requirement_text": "",
            "requirements": [],
            "requirement_summary": None,
            "test_cases": [],
            "review_passed": False,  # 未通过
            "review_comments": [],
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "reviewed",
            "agent_messages": []
        }

        result = should_regenerate(state)
        assert result == "regenerate"

    def test_should_end_when_max_iterations(self):
        """达到最大迭代次数时应该结束"""
        state: AgentState = {
            "requirement_text": "",
            "requirements": [],
            "requirement_summary": None,
            "test_cases": [],
            "review_passed": False,
            "review_comments": [],
            "iteration_count": 2,  # 已达最大
            "max_iterations": 2,
            "feedback": [],
            "current_step": "reviewed",
            "agent_messages": []
        }

        result = should_regenerate(state)
        assert result == "end"


class TestIncrementIteration:
    """测试迭代计数"""

    def test_increment(self):
        """测试迭代计数增加"""
        state: AgentState = {
            "requirement_text": "",
            "requirements": [],
            "requirement_summary": None,
            "test_cases": [],
            "review_passed": None,
            "review_comments": None,
            "iteration_count": 0,
            "max_iterations": 2,
            "feedback": [],
            "current_step": "",
            "agent_messages": []
        }

        result = increment_iteration(state)
        assert result["iteration_count"] == 1


# ============ 工作流集成测试 ============

class TestWorkflowIntegration:
    """工作流集成测试"""

    def test_build_workflow(self):
        """测试构建工作流"""
        workflow = build_workflow()

        # 验证节点存在
        nodes = list(workflow.nodes.keys())
        assert "analyze_requirements" in nodes
        assert "generate_test_cases" in nodes
        assert "review_test_cases" in nodes
        assert "increment_iteration" in nodes

    @patch("agents.workflow.RequirementAnalyzer")
    @patch("agents.workflow.TestCaseGenerator")
    def test_run_workflow_success(self, mock_generator_class, mock_analyzer_class):
        """测试完整工作流执行"""
        # Mock 需求分析
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "requirements": SAMPLE_REQUIREMENTS,
            "summary": "测试摘要"
        }
        mock_analyzer_class.return_value = mock_analyzer

        # Mock 用例生成
        mock_generator = MagicMock()
        mock_generator.generate.return_value = SAMPLE_TEST_CASES
        mock_generator_class.return_value = mock_generator

        # 运行工作流
        result = run_workflow(SAMPLE_REQUIREMENT, max_iterations=2)

        # 验证结果
        assert result["requirements"] == SAMPLE_REQUIREMENTS
        assert len(result["test_cases"]) == 2
        assert result["review_passed"] == True
        assert result["iteration_count"] == 0  # 一次通过，无需迭代


# ============ 运行测试 ============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
