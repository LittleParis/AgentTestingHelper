"""测试用例生成Agent - Pydantic 版本"""
import json
from typing import Dict, Any, List, Union
from pydantic import ValidationError

from core.utils.llm_client import get_llm_client
from core.models.requirement import Requirement
from core.models.test_case import TestCase, TestCaseGenerationResult, TestCaseType, TestStep
from core.models.requirement import Priority


class TestCaseGenerator:
    """测试用例生成Agent - Pydantic 版本"""

    def __init__(self):
        """初始化测试用例生成Agent"""
        self.llm = get_llm_client()

    def generate(self, requirement: Union[Dict[str, Any], Requirement]) -> List[Dict[str, Any]]:
        """
        基于需求生成测试用例（向后兼容接口）

        Args:
            requirement: 结构化需求（字典或 Requirement 模型）

        Returns:
            测试用例列表（字典格式）
        """
        # 转换为 Requirement 模型
        if isinstance(requirement, dict):
            req = self._dict_to_requirement(requirement)
        else:
            req = requirement

        # 调用新的 Pydantic 版本
        result = self.generate_structured(req)

        # 转换为字典格式保持兼容性
        return [tc.model_dump() for tc in result.test_cases]

    def generate_structured(self, requirement: Requirement) -> TestCaseGenerationResult:
        """
        基于需求生成测试用例（新版本，返回 Pydantic 模型）

        Args:
            requirement: Requirement 模型

        Returns:
            TestCaseGenerationResult: 结构化的测试用例生成结果

        Raises:
            ValueError: 当输入参数无效时
            ValidationError: 当 LLM 输出不符合预期格式时
        """
        prompt = self._build_prompt(requirement)

        try:
            # 调用 LLM
            content = self.llm.chat_simple(prompt, temperature=0.7, max_tokens=4096)

            # 解析 JSON 响应
            json_data = self._extract_json(content)

            # 使用 Pydantic 验证和解析
            result = self._parse_llm_response(json_data, requirement.id)

            return result

        except ValidationError as e:
            print(f"[TestCaseGenerator] 数据验证失败: {e}")
            # 降级到简单解析
            return self._fallback_parse(json_data, requirement.id)
        except json.JSONDecodeError as e:
            print(f"[TestCaseGenerator] JSON 解析失败: {e}")
            print(f"原始响应: {content}")
            raise
        except Exception as e:
            print(f"[TestCaseGenerator] 生成失败: {e}")
            raise

    def _dict_to_requirement(self, req_dict: Dict[str, Any]) -> Requirement:
        """将字典转换为 Requirement 模型"""
        try:
            return Requirement.model_validate(req_dict)
        except ValidationError:
            # 如果验证失败，尝试修复
            return Requirement(
                id=req_dict.get("id", "REQ_001"),
                title=req_dict.get("title", "未命名需求"),
                description=req_dict.get("description", "需求描述"),
                priority=Priority(req_dict.get("priority", "medium")),
                acceptance_criteria=req_dict.get("acceptance_criteria", ["基本功能正常"]),
                ui_elements=req_dict.get("ui_elements", [])
            )

    def _build_prompt(self, requirement: Requirement) -> str:
        """构建生成 prompt"""
        req_json = requirement.model_dump_json(indent=2)

        return f"""你是一个资深测试工程师。基于以下需求，生成测试用例。

需求信息：
{req_json}

输出格式（JSON）：
```json
{{
  "test_cases": [
    {{
      "id": "TC_001",
      "requirement_id": "REQ_001",
      "title": "测试用例标题",
      "priority": "high",
      "type": "functional",
      "steps": [
        {{
          "step_number": 1,
          "action": "操作描述（用自然语言）",
          "data": "测试数据",
          "expected": "预期结果"
        }}
      ],
      "expected": "最终预期结果",
      "tags": ["smoke"]
    }}
  ]
}}
```

要求：
1. **ID格式**: 必须使用 TC_001, TC_002 格式
2. **requirement_id**: 必须与需求的 ID 一致（{requirement.id}）
3. **步骤描述**: 清晰，适合 UI 自动化，每个步骤至少 5 个字符
4. **预期结果**: 每个步骤必须有预期结果，至少 3 个字符
5. **测试类型**: functional, ui, api, integration, performance, security
6. **优先级**: high, medium, low
7. **覆盖场景**: 包含正向和负向测试
8. **独立性**: 每个用例独立可执行
9. **数量**: 至少生成 2-3 个测试用例

请直接输出 JSON，不要有其他内容。"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        content = content.strip()

        # 尝试从 markdown 代码块中提取
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

        # 解析 JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复常见的 JSON 格式问题
            content = self._fix_json_format(content)
            return json.loads(content)

    def _fix_json_format(self, content: str) -> str:
        """修复常见的 JSON 格式问题"""
        content = content.strip()

        # 移除可能的前后缀
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]

        # 移除可能的语言标识
        if content.startswith('json'):
            content = content[4:]

        # 确保以 { 开头，} 结尾
        content = content.strip()
        if not content.startswith('{'):
            start = content.find('{')
            if start != -1:
                content = content[start:]

        if not content.endswith('}'):
            end = content.rfind('}')
            if end != -1:
                content = content[:end+1]

        return content

    def _parse_llm_response(self, json_data: Dict[str, Any], requirement_id: str) -> TestCaseGenerationResult:
        """使用 Pydantic 解析 LLM 响应"""
        try:
            test_cases = []
            raw_test_cases = json_data.get("test_cases", [])

            for i, tc_data in enumerate(raw_test_cases):
                try:
                    # 确保必要字段存在
                    tc_data = self._ensure_test_case_fields(tc_data, requirement_id, i + 1)

                    # 验证和创建测试用例对象
                    test_case = TestCase.model_validate(tc_data)
                    test_cases.append(test_case)

                except ValidationError as e:
                    print(f"[TestCaseGenerator] 测试用例 {i+1} 验证失败: {e}")
                    # 尝试修复常见问题
                    fixed_tc = self._fix_test_case_data(tc_data, requirement_id, i + 1)
                    if fixed_tc:
                        test_cases.append(fixed_tc)

            # 创建生成结果
            return TestCaseGenerationResult(
                test_cases=test_cases,
                requirement_id=requirement_id,
                total_count=len(test_cases)
            )

        except ValidationError as e:
            print(f"[TestCaseGenerator] 结果验证失败: {e}")
            raise

    def _ensure_test_case_fields(self, tc_data: Dict, requirement_id: str, index: int) -> Dict:
        """确保测试用例字段完整"""
        data = tc_data.copy()

        # 确保 ID 格式
        if "id" not in data or not data["id"]:
            data["id"] = f"TC_{index:03d}"

        # 确保 requirement_id 一致
        data["requirement_id"] = requirement_id

        # 确保标题存在
        if "title" not in data or not data["title"]:
            data["title"] = f"测试用例 {index}"

        # 确保预期结果存在
        if "expected" not in data or not data["expected"]:
            data["expected"] = "测试通过"

        # 确保 steps 存在且格式正确
        if "steps" not in data or not data["steps"]:
            data["steps"] = [{
                "step_number": 1,
                "action": "执行测试操作",
                "expected": "操作成功"
            }]
        else:
            # 确保步骤序号连续
            for j, step in enumerate(data["steps"]):
                step["step_number"] = j + 1
                if "expected" not in step or not step["expected"]:
                    step["expected"] = "操作成功"

        # 确保 tags 存在
        if "tags" not in data:
            data["tags"] = []

        return data

    def _fix_test_case_data(self, tc_data: Dict, requirement_id: str, index: int) -> TestCase:
        """尝试修复测试用例数据"""
        try:
            # 确保所有必要字段
            fixed_data = self._ensure_test_case_fields(tc_data, requirement_id, index)

            # 验证优先级
            if "priority" not in fixed_data or fixed_data["priority"] not in ["high", "medium", "low"]:
                fixed_data["priority"] = "medium"

            # 验证类型
            valid_types = ["functional", "ui", "api", "integration", "performance", "security"]
            if "type" not in fixed_data or fixed_data["type"] not in valid_types:
                fixed_data["type"] = "functional"

            return TestCase.model_validate(fixed_data)

        except Exception as e:
            print(f"[TestCaseGenerator] 无法修复测试用例数据: {e}")
            # 返回一个最小的有效测试用例
            return TestCase(
                id=f"TC_{index:03d}",
                requirement_id=requirement_id,
                title=f"测试用例 {index}",
                steps=[TestStep(step_number=1, action="执行测试", expected="测试通过")],
                expected="测试通过"
            )

    def _fallback_parse(self, json_data: Dict[str, Any], requirement_id: str) -> TestCaseGenerationResult:
        """降级解析方案（当 Pydantic 验证失败时）"""
        print("[TestCaseGenerator] 使用降级解析方案")

        try:
            test_cases = []
            raw_test_cases = json_data.get("test_cases", [])

            for i, tc_data in enumerate(raw_test_cases):
                # 创建最基本的测试用例对象
                test_case = TestCase(
                    id=tc_data.get("id", f"TC_{i+1:03d}"),
                    requirement_id=requirement_id,
                    title=tc_data.get("title", f"测试用例 {i+1}"),
                    priority=Priority.MEDIUM,
                    type=TestCaseType.FUNCTIONAL,
                    steps=[TestStep(
                        step_number=j+1,
                        action=step.get("action", "执行操作"),
                        data=step.get("data"),
                        expected=step.get("expected", "操作成功")
                    ) for j, step in enumerate(tc_data.get("steps", [{"action": "执行测试"}]))],
                    expected=tc_data.get("expected", "测试通过"),
                    tags=tc_data.get("tags", [])
                )
                test_cases.append(test_case)

            return TestCaseGenerationResult(
                test_cases=test_cases,
                requirement_id=requirement_id,
                total_count=len(test_cases)
            )

        except Exception as e:
            print(f"[TestCaseGenerator] 降级解析也失败: {e}")
            # 返回空结果
            return TestCaseGenerationResult(
                test_cases=[],
                requirement_id=requirement_id,
                total_count=0
            )
