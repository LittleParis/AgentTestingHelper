"""
测试用例评审 Agent - Pydantic 版本

使用 LLM 进行智能评审：
- 用例完整性检查
- 覆盖率分析
- 合理性评估
- 改进建议
"""
import json
from typing import List, Dict, Any, Union
from pydantic import ValidationError

from core.utils.llm_client import get_llm_client
from core.models.requirement import Requirement
from core.models.test_case import TestCase
from core.models.review import (
    ReviewResult, ReviewAllResult, ReviewDimensions, ReviewComment,
    RequirementReviewDetail, CommentType, CommentSeverity
)


class CaseReviewer:
    """测试用例评审 Agent - Pydantic 版本"""

    def __init__(self):
        self.llm = get_llm_client()

    def review(self, requirement: Union[Dict, Requirement], test_cases: Union[List[Dict], List[TestCase]]) -> Dict[str, Any]:
        """
        评审单个需求的测试用例（向后兼容接口）

        Args:
            requirement: 需求对象（字典或 Requirement 模型）
            test_cases: 测试用例列表（字典或 TestCase 模型）

        Returns:
            评审结果字典
        """
        # 转换为 Pydantic 模型
        req = self._to_requirement(requirement)
        tcs = self._to_test_cases(test_cases)

        # 调用新的 Pydantic 版本
        result = self.review_structured(req, tcs)

        return result.to_dict()

    def review_structured(self, requirement: Requirement, test_cases: List[TestCase]) -> ReviewResult:
        """
        评审单个需求的测试用例（新版本，返回 Pydantic 模型）

        Args:
            requirement: Requirement 模型
            test_cases: TestCase 模型列表

        Returns:
            ReviewResult: 结构化的评审结果
        """
        prompt = self._build_review_prompt(requirement, test_cases)

        try:
            response = self.llm.chat_simple(prompt)
            result = self._parse_response(response)
            return result
        except ValidationError as e:
            print(f"[Reviewer] 数据验证失败: {e}")
            return self._fallback_review_result()
        except Exception as e:
            print(f"[Reviewer] 评审失败: {e}")
            return ReviewResult(
                passed=False,
                score=0,
                comments=[ReviewComment(
                    type=CommentType.ERROR,
                    severity=CommentSeverity.HIGH,
                    message=str(e)
                )],
                suggestions=[]
            )

    def review_all(self, requirements: List[Union[Dict, Requirement]], all_test_cases: List[Union[Dict, TestCase]]) -> Dict[str, Any]:
        """
        评审所有需求和测试用例（向后兼容接口）

        Args:
            requirements: 需求列表
            all_test_cases: 所有测试用例

        Returns:
            评审结果字典
        """
        # 转换为 Pydantic 模型
        reqs = [self._to_requirement(r) for r in requirements]
        tcs = [self._to_test_case(tc) if isinstance(tc, dict) else tc for tc in all_test_cases]

        # 调用新的 Pydantic 版本
        result = self.review_all_structured(reqs, tcs)

        return result.to_dict()

    def review_all_structured(self, requirements: List[Requirement], all_test_cases: List[TestCase]) -> ReviewAllResult:
        """
        评审所有需求和测试用例（新版本，返回 Pydantic 模型）

        Args:
            requirements: Requirement 模型列表
            all_test_cases: TestCase 模型列表

        Returns:
            ReviewAllResult: 结构化的整体评审结果
        """
        # 按需求分组测试用例
        cases_by_req = self._group_cases_by_requirement(all_test_cases)

        # 评审每个需求
        details = []
        total_score = 0

        for req in requirements:
            req_id = req.id
            req_cases = cases_by_req.get(req_id, [])

            if not req_cases:
                # 没有对应的测试用例
                details.append(RequirementReviewDetail(
                    requirement_id=req_id,
                    requirement_title=req.title,
                    passed=False,
                    score=0,
                    comments=[ReviewComment(
                        type=CommentType.NO_COVERAGE,
                        severity=CommentSeverity.HIGH,
                        message=f"需求 {req_id} 没有对应的测试用例"
                    )],
                    suggestions=[]
                ))
            else:
                result = self.review_structured(req, req_cases)
                details.append(RequirementReviewDetail(
                    requirement_id=req_id,
                    requirement_title=req.title,
                    passed=result.passed,
                    score=result.score,
                    dimensions=result.dimensions,
                    comments=result.comments,
                    suggestions=result.suggestions
                ))
                total_score += result.score

        # 计算平均分
        avg_score = total_score / len(requirements) if requirements else 0

        # 整体是否通过
        passed = all(d.passed for d in details) and avg_score >= 60

        return ReviewAllResult(
            passed=passed,
            total_score=round(avg_score, 1),
            details=details,
            summary=self._generate_summary(details)
        )

    def _to_requirement(self, req: Union[Dict, Requirement]) -> Requirement:
        """转换为 Requirement 模型"""
        if isinstance(req, Requirement):
            return req
        try:
            return Requirement.model_validate(req)
        except ValidationError:
            return Requirement(
                id=req.get("id", "REQ_001"),
                title=req.get("title", "未命名需求"),
                description=req.get("description", "需求描述"),
                acceptance_criteria=req.get("acceptance_criteria", ["基本功能正常"])
            )

    def _to_test_case(self, tc: Union[Dict, TestCase]) -> TestCase:
        """转换单个测试用例为 TestCase 模型"""
        if isinstance(tc, TestCase):
            return tc
        try:
            return TestCase.model_validate(tc)
        except ValidationError:
            # 简化处理，返回最小有效对象
            from core.models.test_case import TestStep, TestCaseType
            from core.models.requirement import Priority
            return TestCase(
                id=tc.get("id", "TC_001"),
                requirement_id=tc.get("requirement_id", "REQ_001"),
                title=tc.get("title", "测试用例"),
                steps=[TestStep(step_number=1, action="执行测试", expected="通过")],
                expected=tc.get("expected", "测试通过")
            )

    def _to_test_cases(self, tcs: Union[List[Dict], List[TestCase]]) -> List[TestCase]:
        """转换测试用例列表为 TestCase 模型列表"""
        return [self._to_test_case(tc) for tc in tcs]

    def _build_review_prompt(self, requirement: Requirement, test_cases: List[TestCase]) -> str:
        """构建评审提示词"""
        req_json = requirement.model_dump_json(indent=2)
        cases_json = json.dumps([tc.model_dump() for tc in test_cases], ensure_ascii=False, indent=2)

        return f"""你是一位专业的测试用例评审专家。请评审以下测试用例的质量。

## 需求信息
{req_json}

## 测试用例
{cases_json}

## 评审标准

请从以下维度评审，每个维度 0-20 分：

1. **完整性** (0-20分)
   - 每个用例是否有明确的步骤
   - 每个用例是否有预期结果
   - 是否覆盖了所有验收标准

2. **覆盖率** (0-20分)
   - 正向场景是否覆盖
   - 异常场景是否覆盖
   - 边界条件是否覆盖

3. **合理性** (0-20分)
   - 测试步骤是否合理
   - 预期结果是否明确
   - 用例是否可执行

4. **独立性** (0-20分)
   - 用例之间是否独立
   - 是否有依赖关系
   - 是否可以单独执行

5. **清晰度** (0-20分)
   - 描述是否清晰
   - 步骤是否具体
   - 是否易于理解

## 输出格式

请以 JSON 格式输出评审结果：

```json
{{
    "score": 85,
    "passed": true,
    "dimensions": {{
        "completeness": 18,
        "coverage": 17,
        "reasonability": 18,
        "independence": 16,
        "clarity": 16
    }},
    "comments": [
        {{
            "type": "suggestion",
            "severity": "low",
            "message": "建议添加密码为空的边界测试"
        }}
    ],
    "suggestions": [
        "增加密码长度边界值测试",
        "添加账号锁定场景测试"
    ]
}}
```

注意：
- score 是总分（0-100），等于各维度分数之和
- passed 为 true 表示评审通过（score >= 60）
- severity 可选值：high, medium, low
- type 可选值：error, warning, suggestion

请直接输出 JSON，不要有其他内容。"""

    def _parse_response(self, response: str) -> ReviewResult:
        """解析 LLM 响应"""
        content = response.strip()

        # 尝试从 markdown 代码块中提取
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            result = json.loads(content)
            return self._build_review_result(result)
        except json.JSONDecodeError as e:
            print(f"[Reviewer] JSON 解析失败: {e}")
            return ReviewResult(
                passed=False,
                score=0,
                comments=[ReviewComment(
                    type=CommentType.PARSE_ERROR,
                    severity=CommentSeverity.HIGH,
                    message="无法解析评审结果"
                )],
                suggestions=[]
            )

    def _build_review_result(self, data: Dict[str, Any]) -> ReviewResult:
        """构建 ReviewResult 模型"""
        try:
            # 解析维度得分
            dimensions = None
            if "dimensions" in data:
                dim_data = data["dimensions"]
                dimensions = ReviewDimensions(
                    completeness=dim_data.get("completeness", 10),
                    coverage=dim_data.get("coverage", 10),
                    reasonability=dim_data.get("reasonability", 10),
                    independence=dim_data.get("independence", 10),
                    clarity=dim_data.get("clarity", 10)
                )

            # 解析评论
            comments = []
            for c in data.get("comments", []):
                try:
                    comments.append(ReviewComment(
                        type=CommentType(c.get("type", "suggestion")),
                        severity=CommentSeverity(c.get("severity", "medium")),
                        message=c.get("message", "")
                    ))
                except ValueError:
                    comments.append(ReviewComment(
                        type=CommentType.SUGGESTION,
                        severity=CommentSeverity.MEDIUM,
                        message=c.get("message", "")
                    ))

            # 计算分数
            score = data.get("score", 0)
            if dimensions:
                score = dimensions.total()

            return ReviewResult(
                passed=data.get("passed", score >= 60),
                score=score,
                dimensions=dimensions,
                comments=comments,
                suggestions=data.get("suggestions", [])
            )

        except ValidationError as e:
            print(f"[Reviewer] 构建结果失败: {e}")
            return self._fallback_review_result()

    def _fallback_review_result(self) -> ReviewResult:
        """降级评审结果"""
        return ReviewResult(
            passed=False,
            score=0,
            comments=[],
            suggestions=[]
        )

    def _group_cases_by_requirement(self, test_cases: List[TestCase]) -> Dict[str, List[TestCase]]:
        """按需求分组测试用例"""
        groups: Dict[str, List[TestCase]] = {}

        for tc in test_cases:
            req_id = tc.requirement_id
            if req_id not in groups:
                groups[req_id] = []
            groups[req_id].append(tc)

        return groups

    def _generate_summary(self, details: List[RequirementReviewDetail]) -> str:
        """生成评审摘要"""
        passed_count = sum(1 for d in details if d.passed)
        total_count = len(details)

        if passed_count == total_count:
            return f"所有需求评审通过 ({passed_count}/{total_count})"
        else:
            return f"部分需求评审未通过 ({passed_count}/{total_count})"


# ============ 测试 ============

if __name__ == "__main__":
    # 测试评审功能
    reviewer = CaseReviewer()

    requirement = Requirement(
        id="REQ_001",
        title="用户登录",
        description="用户可以通过用户名和密码登录系统",
        acceptance_criteria=[
            "正确的用户名和密码可以成功登录",
            "错误的密码提示'密码错误'",
            "用户名不存在提示'用户不存在'"
        ]
    )

    from core.models.test_case import TestStep
    test_cases = [
        TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="正确登录",
            steps=[
                TestStep(step_number=1, action="输入正确的用户名", expected="显示用户名"),
                TestStep(step_number=2, action="输入正确的密码", expected="显示密码掩码"),
                TestStep(step_number=3, action="点击登录按钮", expected="登录成功")
            ],
            expected="登录成功，跳转到首页"
        ),
        TestCase(
            id="TC_002",
            requirement_id="REQ_001",
            title="密码错误",
            steps=[
                TestStep(step_number=1, action="输入正确的用户名", expected="显示用户名"),
                TestStep(step_number=2, action="输入错误的密码", expected="显示密码掩码"),
                TestStep(step_number=3, action="点击登录按钮", expected="提示错误")
            ],
            expected="提示'密码错误'"
        )
    ]

    result = reviewer.review_structured(requirement, test_cases)
    print(result.model_dump_json(indent=2))
