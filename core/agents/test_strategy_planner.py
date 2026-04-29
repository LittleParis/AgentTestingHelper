"""Requirement-level test strategy planning agent.

This module provides the TestStrategyPlanner class that generates
test strategies using LLM with fallback to heuristic rules.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from pydantic import ValidationError

from core.agents.strategy.fallback_builder import FallbackStrategyBuilder
from core.models.config import get_settings
from core.models.requirement import Priority, Requirement, RequirementType
from core.models.test_strategy import (
    RequirementStrategy,
    TestStrategyPlan,
)
from core.utils.llm_client import get_llm_client


class TestStrategyPlanner:
    """Plan which acceptance points deserve deep coverage.

    This class generates test strategies using LLM with structured output.
    When LLM is unavailable, it falls back to heuristic rules.
    """

    def __init__(self, config: Optional["StrategyConfig"] = None):
        """Initialize planner with optional configuration.

        Args:
            config: Strategy configuration for weights and thresholds
        """
        self.llm = get_llm_client()
        self.config = config or get_settings().get_strategy_config()
        self._fallback_builder = FallbackStrategyBuilder(self.config)

    def plan(
        self,
        requirement_text: str,
        analyzed_requirements: Iterable[Dict[str, Any] | Requirement],
    ) -> Dict[str, Any]:
        """Backward-compatible dict interface.

        Args:
            requirement_text: Raw requirement document text
            analyzed_requirements: List of analyzed requirements

        Returns:
            Strategy plan as dictionary
        """
        return self.plan_structured(requirement_text, analyzed_requirements).to_dict()

    def plan_structured(
        self,
        requirement_text: str,
        analyzed_requirements: Iterable[Dict[str, Any] | Requirement],
    ) -> TestStrategyPlan:
        """Generate a structured test-strategy plan.

        Args:
            requirement_text: Raw requirement document text
            analyzed_requirements: List of analyzed requirements

        Returns:
            TestStrategyPlan instance
        """
        requirements = [self._ensure_requirement(item) for item in analyzed_requirements]

        if not requirements:
            return TestStrategyPlan(
                overall_summary="没有可用的结构化需求，策略规划已跳过。",
                requirement_strategies=[],
                total_suggested_case_budget=0,
                fallback_used=True,
                metadata={"reason": "no_requirements"},
            )

        prompt = self._build_prompt(requirement_text, requirements)

        try:
            result = self.llm.invoke_structured(
                TestStrategyPlan,
                prompt,
                operation="test_strategy_planning",
                temperature=self.config.strategy_temperature,
            )
            plan = result if isinstance(result, TestStrategyPlan) else TestStrategyPlan.model_validate(result)
            return self._normalize_plan(plan, requirements)
        except Exception as exc:
            print(f"[TestStrategyPlanner] Structured strategy planning failed: {exc}")
            return self._fallback_plan(requirement_text, requirements, reason=str(exc))

    def _build_prompt(self, requirement_text: str, requirements: List[Requirement]) -> str:
        """Build the LLM prompt for strategy planning.

        Args:
            requirement_text: Raw requirement document text
            requirements: List of analyzed requirements

        Returns:
            Prompt string for LLM
        """
        requirements_json = json.dumps(
            [self._requirement_to_dict(requirement) for requirement in requirements],
            ensure_ascii=False,
            indent=2,
        )
        return f"""你是资深测试策略专家。请基于下面的需求文档和结构化需求，输出一份"按验收点粒度"的测试策略方案。

需求文档原文：
{requirement_text}

结构化需求：
{requirements_json}

请严格遵守以下规则输出结构化结果：
1. 必须覆盖结构化需求中的每一个 requirement_id，且每个 requirement_id 只出现一次。
2. 策略要细化到验收点粒度。每个 focus_point 通常对应一条 acceptance_criteria，或文档中一条明确的业务预期。
3. 枚举值只能使用下面这些固定取值：
   - focus_level: critical | major | normal | light
   - execution_mode: deep | standard | smoke
   - coverage_axes: happy_path | negative | boundary | exception | recovery | permission | data_validation
   - overall_risk: critical | high | medium | low
4. case_weight 只能是 3、2、1。
5. 默认判断原则：
   - 涉及资金、支付结果、提交动作、状态变更、权限、安全、失败恢复、回滚、重试、幂等、人工审核、审计、风控的点，优先提升到 major 或 critical。
   - 页面加载、字段显隐、普通导航、URL 检查、弱提示、纯展示类检查，默认降为 light 或 normal。
   - 如果登录只是多流程文档里的前置步骤，且文档没有明确强调登录风险，通常保持为 smoke 或 standard。
   - 如果文档明确强调失败处理、边界行为、重试、幂等、人工审核或回滚，要自动提升对应 focus_point。
6. suggested_case_budget 要紧凑且可解释：
   - critical 点通常对应 2-3 条 case
   - major 点通常对应 1-2 条 case
   - normal 点通常对应 1 条 case
   - light 点通常并入 smoke 或主路径 case，不单独膨胀
7. strategy_summary 和 overall_summary 要简洁、具体、可审查。
8. 不要为了凑数制造 filler focus points。
9. 只返回符合结构化模型的内容，不要输出额外解释。
"""

    def _normalize_plan(self, plan: TestStrategyPlan, requirements: List[Requirement]) -> TestStrategyPlan:
        """Normalize the plan to ensure all requirements are covered.

        Args:
            plan: The plan from LLM
            requirements: List of requirements to cover

        Returns:
            Normalized TestStrategyPlan
        """
        normalized_strategies: List[RequirementStrategy] = []

        for requirement in requirements:
            existing = plan.get_strategy_for_requirement(requirement.id)
            if existing is None:
                existing = self._fallback_builder.build_requirement_strategy(
                    requirement, multi_flow=len(requirements) > 1
                )
            normalized_strategies.append(existing)

        return TestStrategyPlan(
            strategy_version=plan.strategy_version or "v1",
            overall_summary=plan.overall_summary,
            requirement_strategies=normalized_strategies,
            total_suggested_case_budget=sum(item.suggested_case_budget for item in normalized_strategies),
            fallback_used=plan.fallback_used,
            metadata=plan.metadata,
        )

    def _fallback_plan(
        self,
        requirement_text: str,
        requirements: List[Requirement],
        *,
        reason: str,
    ) -> TestStrategyPlan:
        """Build a fallback plan using heuristic rules.

        Args:
            requirement_text: Raw requirement document text
            requirements: List of requirements
            reason: Reason for fallback

        Returns:
            TestStrategyPlan built from heuristic rules
        """
        multi_flow = len(requirements) > 1
        strategies = [
            self._fallback_builder.build_requirement_strategy(requirement, multi_flow=multi_flow)
            for requirement in requirements
        ]
        summary = (
            "由于 LLM 策略规划不可用，当前结果由本地启发式规则回退生成。"
            f" 文档长度={len(requirement_text or '')}，需求数={len(requirements)}。"
        )
        return TestStrategyPlan(
            overall_summary=summary,
            requirement_strategies=strategies,
            total_suggested_case_budget=sum(item.suggested_case_budget for item in strategies),
            fallback_used=True,
            metadata={"reason": reason[:200]},
        )

    def _ensure_requirement(self, item: Dict[str, Any] | Requirement) -> Requirement:
        """Ensure item is a Requirement instance.

        Args:
            item: Dict or Requirement instance

        Returns:
            Requirement instance
        """
        if isinstance(item, Requirement):
            return item

        try:
            return Requirement.model_validate(item)
        except ValidationError:
            payload = dict(item or {})
            priority_value = str(payload.get("priority") or "medium")
            type_value = str(payload.get("type") or "functional")
            return Requirement(
                id=str(payload.get("id") or "REQ_001"),
                title=str(payload.get("title") or "Untitled requirement"),
                description=str(payload.get("description") or "Requirement description is missing."),
                priority=Priority(priority_value if priority_value in {"high", "medium", "low"} else "medium"),
                type=RequirementType(
                    type_value
                    if type_value in {"functional", "non_functional", "business", "technical"}
                    else "functional"
                ),
                acceptance_criteria=payload.get("acceptance_criteria") or ["Core flow works correctly."],
                ui_elements=payload.get("ui_elements") or [],
            )

    def _requirement_to_dict(self, requirement: Requirement) -> dict:
        """Convert Requirement to dictionary.

        Args:
            requirement: Requirement instance

        Returns:
            Dictionary representation
        """
        return requirement.model_dump()
