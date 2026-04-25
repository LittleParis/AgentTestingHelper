"""
测试需求分析Agent的核心功能 - pytest 标准格式

Issue #42: 将自定义测试框架改写为标准 pytest 格式
"""
import json
import pytest

from core.models.requirement import Requirement, RequirementAnalysisResult, Priority, RequirementType


class MockLLMClient:
    """模拟LLM客户端"""
    def chat_simple(self, prompt, **kwargs):
        return """```json
{
  "requirements": [
    {
      "id": "REQ_001",
      "title": "用户登录功能",
      "description": "用户可以通过用户名和密码登录系统，支持记住密码功能",
      "priority": "high",
      "type": "functional",
      "acceptance_criteria": [
        "正确的用户名和密码可以成功登录",
        "错误的密码提示'密码错误'",
        "用户名不存在提示'用户不存在'"
      ],
      "ui_elements": ["用户名输入框", "密码输入框", "登录按钮"]
    }
  ],
  "summary": "识别出1个高优先级功能需求，涉及用户认证",
  "total_count": 1
}
```"""


class RequirementAnalyzerCore:
    """需求分析Agent核心功能（简化版）"""

    def __init__(self):
        self.llm = MockLLMClient()

    def analyze_structured(self, requirement_text: str) -> RequirementAnalysisResult:
        """分析需求文档，返回Pydantic模型"""
        if not requirement_text or len(requirement_text.strip()) < 10:
            raise ValueError("需求文档内容太短，至少需要10个字符")

        content = self.llm.chat_simple("prompt")
        json_data = self._extract_json(content)
        result = self._parse_llm_response(json_data)
        return result

    def analyze(self, requirement_text: str) -> dict:
        """向后兼容的字典接口"""
        result = self.analyze_structured(requirement_text)
        return result.to_dict()

    def _extract_json(self, content: str) -> dict:
        """从LLM响应中提取JSON"""
        content = content.strip()

        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()

        return json.loads(content)

    def _parse_llm_response(self, json_data: dict) -> RequirementAnalysisResult:
        """使用Pydantic解析LLM响应"""
        requirements = []
        raw_requirements = json_data.get("requirements", [])

        for i, req_data in enumerate(raw_requirements):
            if "id" not in req_data:
                req_data["id"] = f"REQ_{i+1:03d}"
            requirement = Requirement(**req_data)
            requirements.append(requirement)

        result_data = {
            "requirements": requirements,
            "summary": json_data.get("summary", "需求分析完成"),
            "total_count": len(requirements)
        }

        return RequirementAnalysisResult(**result_data)


# ============ pytest 测试类 ============

class TestRequirementAnalyzerCore:
    """测试需求分析Agent核心功能"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return RequirementAnalyzerCore()

    @pytest.fixture
    def valid_requirement(self):
        """有效的需求文档"""
        return """
        # 用户登录功能

        ## 功能描述
        用户可以通过用户名和密码登录系统。

        ## 验收标准
        1. 正确的用户名和密码可以成功登录
        2. 错误的密码提示"密码错误"
        3. 用户名不存在提示"用户不存在"
        """

    def test_analyze_structured_returns_pydantic_model(self, analyzer, valid_requirement):
        """测试 analyze_structured 返回 Pydantic 模型"""
        result = analyzer.analyze_structured(valid_requirement)

        assert isinstance(result, RequirementAnalysisResult)
        assert result.total_count == 1
        assert "需求" in result.summary

    def test_analyze_returns_dict(self, analyzer, valid_requirement):
        """测试 analyze 返回字典（向后兼容）"""
        result = analyzer.analyze(valid_requirement)

        assert isinstance(result, dict)
        assert "requirements" in result
        assert "summary" in result
        assert "total_count" in result

    def test_requirement_fields_valid(self, analyzer, valid_requirement):
        """测试需求字段验证"""
        result = analyzer.analyze_structured(valid_requirement)

        assert len(result.requirements) == 1
        req = result.requirements[0]

        assert req.id == "REQ_001"
        assert req.title == "用户登录功能"
        assert req.priority == Priority.HIGH
        assert req.type == RequirementType.FUNCTIONAL
        assert len(req.acceptance_criteria) == 3
        assert len(req.ui_elements) == 3

    def test_empty_input_raises_error(self, analyzer):
        """测试空输入抛出异常"""
        with pytest.raises(ValueError, match="至少需要10个字符"):
            analyzer.analyze_structured("")

    def test_short_input_raises_error(self, analyzer):
        """测试过短输入抛出异常"""
        with pytest.raises(ValueError, match="至少需要10个字符"):
            analyzer.analyze_structured("短")

    def test_get_requirements_by_priority(self, analyzer, valid_requirement):
        """测试按优先级筛选需求"""
        result = analyzer.analyze_structured(valid_requirement)

        high_priority = result.get_requirements_by_priority(Priority.HIGH)
        medium_priority = result.get_requirements_by_priority(Priority.MEDIUM)
        low_priority = result.get_requirements_by_priority(Priority.LOW)

        assert len(high_priority) == 1
        assert len(medium_priority) == 0
        assert len(low_priority) == 0

    def test_get_requirements_by_type(self, analyzer, valid_requirement):
        """测试按类型筛选需求"""
        result = analyzer.analyze_structured(valid_requirement)

        functional = result.get_requirements_by_type(RequirementType.FUNCTIONAL)
        non_functional = result.get_requirements_by_type(RequirementType.NON_FUNCTIONAL)

        assert len(functional) == 1
        assert len(non_functional) == 0

    def test_json_serialization(self, analyzer, valid_requirement):
        """测试JSON序列化"""
        result = analyzer.analyze_structured(valid_requirement)

        json_str = result.model_dump_json(indent=2)
        parsed = json.loads(json_str)

        assert "requirements" in parsed
        assert "summary" in parsed
        assert parsed["total_count"] == 1

    def test_to_dict_consistency(self, analyzer, valid_requirement):
        """测试字典转换一致性"""
        result_model = analyzer.analyze_structured(valid_requirement)
        result_dict = analyzer.analyze(valid_requirement)

        assert result_model.summary == result_dict["summary"]
        assert result_model.total_count == result_dict["total_count"]


class TestJsonExtraction:
    """测试JSON提取功能"""

    @pytest.fixture
    def analyzer(self):
        return RequirementAnalyzerCore()

    def test_extract_from_json_code_block(self, analyzer):
        """测试从json代码块提取"""
        content = """```json
{"test": "value"}
```"""
        result = analyzer._extract_json(content)
        assert result == {"test": "value"}

    def test_extract_from_plain_json(self, analyzer):
        """测试从纯JSON提取"""
        content = '{"test": "value"}'
        result = analyzer._extract_json(content)
        assert result == {"test": "value"}

    def test_extract_from_generic_code_block(self, analyzer):
        """测试从通用代码块提取"""
        content = """```
{"test": "value"}
```"""
        result = analyzer._extract_json(content)
        assert result == {"test": "value"}
