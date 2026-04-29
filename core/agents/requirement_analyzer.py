"""Requirement analysis agent with structured-output support."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from pydantic import ValidationError

from core.models.requirement import Priority, Requirement, RequirementAnalysisResult, RequirementType
from core.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class RequirementAnalyzer:
    """Analyze requirement documents into structured requirements."""

    ANALYSIS_TEMPERATURE = 0.1

    def __init__(self):
        self.llm = get_llm_client()

    def analyze(self, requirement_text: str) -> Dict[str, Any]:
        """Backward-compatible dict interface."""
        result = self.analyze_structured(requirement_text)
        return result.to_dict()

    def analyze_structured(self, requirement_text: str) -> RequirementAnalysisResult:
        """Analyze a requirement document with structured output."""
        if not requirement_text or len(requirement_text.strip()) < 10:
            raise ValueError("需求文档内容过短，至少需要 10 个字符。")

        prompt = self._build_prompt(requirement_text)

        try:
            logger.info(
                "Requirement analysis using low temperature: operation=requirement_analysis temperature=%s",
                self.ANALYSIS_TEMPERATURE,
            )
            result = self.llm.invoke_structured(
                RequirementAnalysisResult,
                prompt,
                operation="requirement_analysis",
                temperature=self.ANALYSIS_TEMPERATURE,
            )
            if isinstance(result, RequirementAnalysisResult):
                return result
            return RequirementAnalysisResult.model_validate(result)
        except ValidationError as exc:
            print(f"[RequirementAnalyzer] 数据校验失败: {exc}")
            return self._fallback_invoke(prompt)
        except Exception as exc:
            print(f"[RequirementAnalyzer] 结构化输出失败: {exc}")
            return self._fallback_invoke(prompt)

    def _fallback_invoke(self, prompt: str) -> RequirementAnalysisResult:
        """Fallback by asking for plain JSON and parsing it locally."""
        print("[RequirementAnalyzer] 使用降级解析方案")
        logger.info(
            "Requirement analysis fallback using low temperature: operation=requirement_analysis_fallback temperature=%s",
            self.ANALYSIS_TEMPERATURE,
        )

        try:
            content = self.llm.chat_simple(
                prompt,
                temperature=self.ANALYSIS_TEMPERATURE,
                max_tokens=4096,
            )
            json_data = self._extract_json(content)
            return self._parse_llm_response(json_data)
        except Exception as exc:
            print(f"[RequirementAnalyzer] 降级解析也失败: {exc}")
            raise

    def _build_prompt(self, requirement_text: str) -> str:
        return f"""你是专业的需求分析专家。请分析下面的需求文档，并提取适合测试生成的顶层需求。

需求文档内容：
{requirement_text}

请严格输出如下 JSON：

```json
{{
  "requirements": [
    {{
      "id": "REQ_001",
      "title": "需求标题",
      "description": "详细描述",
      "priority": "high|medium|low",
      "type": "functional|non_functional|business|technical",
      "acceptance_criteria": ["验收标准1", "验收标准2"],
      "ui_elements": ["涉及的UI元素"]
    }}
  ],
  "summary": "需求概述",
  "total_count": 1
}}
```

分析规则：
1. 如果文档描述的是多段业务流程，请优先按“有业务意义的子流程”聚合需求，例如登录、下单、支付，而不是把每个输入框、URL 检查、按钮显隐都拆成独立需求。
2. URL、页面加载、字段可见、空输入校验、错误提示等内容，默认应作为对应主流程的 acceptance_criteria，而不是单独新增顶层 requirement，除非文档明确把它写成独立业务目标。
3. 如果文档里出现登录、下单、支付这类串联流程，请输出 2-4 个主 requirement，而不是把每条 bullet 都拆平。
4. 每个 requirement 都要足够完整，方便后续为该 requirement 规划测试预算。
5. total_count 必须严格等于 requirements 数组长度。

字段要求：
1. requirement ID 必须使用 REQ_001、REQ_002 格式。
2. priority 只能是 high、medium、low。
3. type 只能是 functional、non_functional、business、technical。
4. acceptance_criteria 至少 1 条，每条至少 5 个字符。
5. description 至少 10 个字符。
6. title 长度 1-200 个字符。

只输出 JSON，不要输出解释。"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from a raw LLM response."""
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

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return json.loads(self._fix_json_format(content))

    def _fix_json_format(self, content: str) -> str:
        """Repair a few common JSON formatting issues."""
        content = content.strip()
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        if content.startswith("json"):
            content = content[4:]

        content = content.strip()
        if not content.startswith("{"):
            start = content.find("{")
            if start != -1:
                content = content[start:]
        if not content.endswith("}"):
            end = content.rfind("}")
            if end != -1:
                content = content[: end + 1]
        return content

    def _parse_llm_response(self, json_data: Dict[str, Any]) -> RequirementAnalysisResult:
        """Parse plain JSON into the requirement result model."""
        requirements = []
        raw_requirements = json_data.get("requirements", [])

        for index, req_data in enumerate(raw_requirements, start=1):
            try:
                req_data = dict(req_data or {})
                if not req_data.get("id"):
                    req_data["id"] = f"REQ_{index:03d}"
                requirements.append(Requirement.model_validate(req_data))
            except ValidationError as exc:
                print(f"[RequirementAnalyzer] 需求 {index} 校验失败: {exc}")
                fixed_req = self._fix_requirement_data(req_data, index)
                if fixed_req:
                    requirements.append(fixed_req)

        result_data = {
            "requirements": requirements,
            "summary": json_data.get("summary", "需求分析完成，已整理主流程需求。"),
            "total_count": len(requirements),
        }
        return RequirementAnalysisResult.model_validate(result_data)

    def _fix_requirement_data(self, req_data: dict, index: int) -> Optional[Requirement]:
        """Attempt to repair a malformed requirement payload."""
        try:
            fixed_data = dict(req_data or {})
            fixed_data.setdefault("id", f"REQ_{index:03d}")
            fixed_data.setdefault("title", f"需求 {index}")

            description = str(fixed_data.get("description") or "").strip()
            if len(description) < 10:
                fixed_data["description"] = f"这是第 {index} 个需求的详细描述。"

            criteria = fixed_data.get("acceptance_criteria") or []
            cleaned_criteria = [str(item).strip() for item in criteria if len(str(item).strip()) >= 5]
            if not cleaned_criteria:
                cleaned_criteria = ["基本功能可以正常工作。"]
            fixed_data["acceptance_criteria"] = cleaned_criteria

            if fixed_data.get("priority") not in {"high", "medium", "low"}:
                fixed_data["priority"] = "medium"
            if fixed_data.get("type") not in {
                "functional",
                "non_functional",
                "business",
                "technical",
            }:
                fixed_data["type"] = "functional"

            fixed_data["ui_elements"] = fixed_data.get("ui_elements") or []
            return Requirement.model_validate(fixed_data)
        except Exception as exc:
            print(f"[RequirementAnalyzer] 无法修复需求数据: {exc}")
            return None

    def _fallback_parse(self, json_data: Dict[str, Any]) -> RequirementAnalysisResult:
        """Loose fallback parser kept for backward compatibility."""
        try:
            requirements = []
            raw_requirements = json_data.get("requirements", [])

            for index, req_data in enumerate(raw_requirements, start=1):
                req_data = dict(req_data or {})
                requirements.append(
                    Requirement(
                        id=req_data.get("id", f"REQ_{index:03d}"),
                        title=req_data.get("title", f"需求 {index}"),
                        description=req_data.get("description", "需求描述待补充。"),
                        priority=Priority.MEDIUM,
                        type=RequirementType.FUNCTIONAL,
                        acceptance_criteria=req_data.get("acceptance_criteria", ["基本功能正常。"]),
                        ui_elements=req_data.get("ui_elements", []),
                    )
                )

            return RequirementAnalysisResult(
                requirements=requirements,
                summary=json_data.get("summary", "需求分析完成，使用了降级模式。"),
                total_count=len(requirements),
            )
        except Exception as exc:
            print(f"[RequirementAnalyzer] 降级解析也失败: {exc}")
            return RequirementAnalysisResult(
                requirements=[],
                summary="需求分析失败，未得到可用结果。",
                total_count=0,
            )
