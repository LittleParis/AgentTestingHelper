"""
测试用例评审 Agent

使用 LLM 进行智能评审：
- 用例完整性检查
- 覆盖率分析
- 合理性评估
- 改进建议
"""
import json
from typing import List, Dict, Any
from utils.llm_client import get_llm_client


class CaseReviewer:
    """测试用例评审 Agent"""

    def __init__(self):
        self.llm = get_llm_client()

    def review(self, requirement: Dict[str, Any], test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评审单个需求的测试用例

        Args:
            requirement: 需求对象
            test_cases: 该需求对应的测试用例列表

        Returns:
            {
                "passed": bool,
                "score": float,  # 0-100
                "comments": List[dict],
                "suggestions": List[str]
            }
        """
        prompt = self._build_review_prompt(requirement, test_cases)

        try:
            response = self.llm.chat_simple(prompt)
            result = self._parse_response(response)
            return result
        except Exception as e:
            print(f"[Reviewer] 评审失败: {e}")
            return {
                "passed": False,
                "score": 0,
                "comments": [{"type": "error", "message": str(e)}],
                "suggestions": []
            }

    def review_all(self, requirements: List[Dict], all_test_cases: List[Dict]) -> Dict[str, Any]:
        """
        评审所有需求和测试用例

        Args:
            requirements: 需求列表
            all_test_cases: 所有测试用例

        Returns:
            {
                "passed": bool,
                "total_score": float,
                "details": List[dict],  # 每个需求的评审结果
                "summary": str
            }
        """
        # 按需求分组测试用例
        cases_by_req = self._group_cases_by_requirement(all_test_cases)

        # 评审每个需求
        details = []
        total_score = 0

        for req in requirements:
            req_id = req.get("id", "")
            req_cases = cases_by_req.get(req_id, [])

            if not req_cases:
                details.append({
                    "requirement_id": req_id,
                    "requirement_title": req.get("title", ""),
                    "passed": False,
                    "score": 0,
                    "comments": [{"type": "no_coverage", "severity": "high",
                                  "message": f"需求 {req_id} 没有对应的测试用例"}]
                })
            else:
                result = self.review(req, req_cases)
                details.append({
                    "requirement_id": req_id,
                    "requirement_title": req.get("title", ""),
                    **result
                })
                total_score += result["score"]

        # 计算总分
        avg_score = total_score / len(requirements) if requirements else 0

        # 整体是否通过
        passed = all(d["passed"] for d in details) and avg_score >= 60

        return {
            "passed": passed,
            "total_score": round(avg_score, 1),
            "details": details,
            "summary": self._generate_summary(details)
        }

    def _build_review_prompt(self, requirement: Dict, test_cases: List[Dict]) -> str:
        """构建评审提示词"""
        req_json = json.dumps(requirement, ensure_ascii=False, indent=2)
        cases_json = json.dumps(test_cases, ensure_ascii=False, indent=2)

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
- score 是总分（0-100）
- passed 为 true 表示评审通过（score >= 60）
- severity 可选值：high, medium, low
- type 可选值：error, warning, suggestion

请直接输出 JSON，不要有其他内容。"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        # 提取 JSON
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

            # 确保必要字段存在
            return {
                "passed": result.get("passed", False),
                "score": result.get("score", 0),
                "dimensions": result.get("dimensions", {}),
                "comments": result.get("comments", []),
                "suggestions": result.get("suggestions", [])
            }
        except json.JSONDecodeError as e:
            print(f"[Reviewer] JSON 解析失败: {e}")
            return {
                "passed": False,
                "score": 0,
                "comments": [{"type": "parse_error", "message": "无法解析评审结果"}],
                "suggestions": []
            }

    def _group_cases_by_requirement(self, test_cases: List[Dict]) -> Dict[str, List[Dict]]:
        """按需求分组测试用例"""
        groups = {}

        for tc in test_cases:
            # 优先使用 requirement_id 字段
            req_id = tc.get("requirement_id")
            if req_id:
                if req_id not in groups:
                    groups[req_id] = []
                groups[req_id].append(tc)
                continue

            # 备选：从 TC_001 提取 REQ_001
            tc_id = tc.get("id", "")
            if tc_id.startswith("TC_"):
                parts = tc_id.split("_")
                if len(parts) >= 2:
                    req_num = parts[1]
                    req_id = f"REQ_{req_num}"

                    if req_id not in groups:
                        groups[req_id] = []
                    groups[req_id].append(tc)

        return groups

    def _generate_summary(self, details: List[Dict]) -> str:
        """生成评审摘要"""
        passed_count = sum(1 for d in details if d["passed"])
        total_count = len(details)

        if passed_count == total_count:
            return f"所有需求评审通过 ({passed_count}/{total_count})"
        else:
            return f"部分需求评审未通过 ({passed_count}/{total_count})"


# ============ 测试 ============

if __name__ == "__main__":
    # 测试评审功能
    reviewer = CaseReviewer()

    requirement = {
        "id": "REQ_001",
        "title": "用户登录",
        "description": "用户可以通过用户名和密码登录系统",
        "acceptance_criteria": [
            "正确的用户名和密码可以成功登录",
            "错误的密码提示'密码错误'",
            "用户名不存在提示'用户不存在'"
        ]
    }

    test_cases = [
        {
            "id": "TC_001",
            "title": "正确登录",
            "steps": ["输入正确的用户名", "输入正确的密码", "点击登录按钮"],
            "expected": "登录成功，跳转到首页"
        },
        {
            "id": "TC_002",
            "title": "密码错误",
            "steps": ["输入正确的用户名", "输入错误的密码", "点击登录按钮"],
            "expected": "提示'密码错误'"
        }
    ]

    result = reviewer.review(requirement, test_cases)
    print(json.dumps(result, ensure_ascii=False, indent=2))
