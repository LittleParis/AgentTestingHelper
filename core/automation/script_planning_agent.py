"""Agentic planner that builds structured script execution plans."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from core.automation.script_plan_validator import PlanValidator
from core.automation.script_tools import (
    ActionStrategyTool,
    AssertionStrategyTool,
    CredentialPolicyTool,
    ScenarioClassifierTool,
    SelectorCatalogTool,
    StrategyFocusResolver,
)
from core.models.script_plan import (
    ExecutionPolicy,
    ExecutionTarget,
    FallbackPolicy,
    PlannerDecisionTrace,
    ScenarioPlan,
    ScriptExecutionPlan,
    ScriptSetupPlan,
)

try:
    from core.utils.llm_client import get_llm_client as _get_llm_client
except Exception:  # pragma: no cover - optional in test-only environments
    _get_llm_client = None

get_llm_client = _get_llm_client


class ScriptPlanningAgent:
    """Build a structured execution plan before rendering code."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self._llm_client = None
        self.scenario_classifier = ScenarioClassifierTool()
        self.selector_catalog = SelectorCatalogTool()
        self.credential_policy = CredentialPolicyTool()
        self.action_strategy = ActionStrategyTool()
        self.assertion_strategy = AssertionStrategyTool()
        self.focus_resolver = StrategyFocusResolver()
        self.validator = PlanValidator()

    @property
    def llm_client(self):
        if self._llm_client is None and self.use_llm:
            if get_llm_client is None:
                return None
            self._llm_client = get_llm_client()
        return self._llm_client

    def plan(
        self,
        test_case: Dict[str, Any],
        *,
        strategy_context: Optional[Dict[str, Any]],
        scenario_config: Optional[Dict[str, Any]],
        page_url: str,
    ) -> ScriptExecutionPlan:
        baseline = self._build_deterministic_plan(
            test_case=test_case,
            strategy_context=strategy_context,
            scenario_config=scenario_config,
            page_url=page_url,
        )

        if not self.use_llm or self.llm_client is None:
            return self.validator.validate(
                baseline,
                scenario_config=scenario_config,
                tc_type=str(test_case.get("type") or "functional"),
                tc_title=str(test_case.get("title") or ""),
                steps=test_case.get("steps") or [],
            )

        try:
            llm_plan = self.llm_client.invoke_structured(
                ScriptExecutionPlan,
                self._build_prompt(test_case, strategy_context, baseline),
                operation="script_execution_planning",
            )
            merged = self._merge_plan(baseline, llm_plan if isinstance(llm_plan, ScriptExecutionPlan) else ScriptExecutionPlan.model_validate(llm_plan))
            return self.validator.validate(
                merged,
                scenario_config=scenario_config,
                tc_type=str(test_case.get("type") or "functional"),
                tc_title=str(test_case.get("title") or ""),
                steps=test_case.get("steps") or [],
            )
        except Exception as exc:
            baseline.metadata["llm_planning_error"] = str(exc)
            return self.validator.validate(
                baseline,
                scenario_config=scenario_config,
                tc_type=str(test_case.get("type") or "functional"),
                tc_title=str(test_case.get("title") or ""),
                steps=test_case.get("steps") or [],
            )

    def plan_many(
        self,
        test_cases: List[Dict[str, Any]],
        *,
        strategy_plan: Optional[Dict[str, Any]],
        scenario_config: Optional[Dict[str, Any]],
        page_url: str,
    ) -> List[ScriptExecutionPlan]:
        plans: List[ScriptExecutionPlan] = []
        for test_case in test_cases:
            strategy_context = self.focus_resolver.resolve_for_test_case(test_case, strategy_plan)
            plans.append(
                self.plan(
                    test_case,
                    strategy_context=strategy_context,
                    scenario_config=scenario_config,
                    page_url=page_url,
                )
            )
        return plans

    def _build_deterministic_plan(
        self,
        *,
        test_case: Dict[str, Any],
        strategy_context: Optional[Dict[str, Any]],
        scenario_config: Optional[Dict[str, Any]],
        page_url: str,
    ) -> ScriptExecutionPlan:
        steps = list(test_case.get("steps") or [])
        scenario_type = self.scenario_classifier.classify(
            steps,
            page_url,
            scenario_config=scenario_config,
            tc_title=str(test_case.get("title") or ""),
        )
        selectors = self.selector_catalog.get_catalog(scenario_type)
        credential_policy = self.credential_policy.resolve(
            scenario_type=scenario_type,
            scenario_config=scenario_config,
            tc_type=str(test_case.get("type") or "functional"),
            tc_title=str(test_case.get("title") or ""),
            steps=steps,
        )
        execution_mode = str((strategy_context or {}).get("execution_mode") or "standard")

        scenario_plan = ScenarioPlan(
            scenario_type=scenario_type,
            risk_level=self._infer_risk_level(strategy_context),
            execution_policy=self._infer_execution_policy(execution_mode, scenario_type),
            allow_ai_only=scenario_type not in {"login_only"},
            requires_runtime_credentials=credential_policy["requires_runtime_credentials"],
            selectors=selectors,
            tags=list(test_case.get("tags") or []),
        )
        setup_plan = ScriptSetupPlan(
            page_url=page_url,
            initial_wait_ms=1500,
            required_env_vars=list(credential_policy["required_env_vars"]),
            mask_locator_aliases=["identifierInput", "passwordInput"] if scenario_type == "login_only" else [],
        )

        focus_points = list((strategy_context or {}).get("focus_points") or [])
        step_plans = []
        for index, step in enumerate(steps, start=1):
            focus_hint = focus_points[min(index - 1, len(focus_points) - 1)] if focus_points else {"execution_mode": execution_mode}
            step_plan = self.action_strategy.plan_step(
                step_number=index,
                action=str(step.get("action", "")),
                data=str(step.get("data", "")),
                expected=str(step.get("expected", "")),
                scenario_type=scenario_type,
                credential_policy=credential_policy,
                focus_hint=focus_hint,
            )
            step_plan.verify_prompt = str(step.get("expected", "") or "")
            step_plan.assertion_intents = self.assertion_strategy.build_step_assertions(
                action=step_plan.original_action,
                expected=step_plan.original_expected,
                verify_prompt=step_plan.verify_prompt,
                data=step_plan.normalized_data,
                scenario_type=scenario_type,
            )
            step_plans.append(step_plan)

        final_expected = str(test_case.get("expected") or "")
        plan = ScriptExecutionPlan(
            testcase_id=str(test_case.get("id") or "TC_XXX"),
            title=str(test_case.get("title") or "Untitled test case"),
            requirement_id=test_case.get("requirement_id"),
            scenario=scenario_plan,
            setup=setup_plan,
            steps=step_plans,
            final_assertions=self.assertion_strategy.build_final_assertions(
                expected=final_expected,
                scenario_type=scenario_type,
            ),
            fallback_policy=FallbackPolicy.REPAIR_WITH_RULES if self.use_llm else FallbackPolicy.DETERMINISTIC,
            metadata={
                "source": "deterministic_baseline",
                "final_expected": final_expected,
                "reasoning_summary": self._build_reasoning_summary(test_case, strategy_context, scenario_type),
                "confidence": 0.66 if scenario_type != "generic" else 0.52,
                "strategy_context": strategy_context or {},
                "scenario_config": scenario_config or {},
            },
        )

        if scenario_type == "login_only":
            success_signal = (scenario_config or {}).get("success_signal") or {}
            plan.metadata.update(
                {
                    "success_signal_value": str(success_signal.get("value") or "LianLian"),
                    "success_signal_type": str(success_signal.get("type") or "visual_text_or_logo"),
                    "manual_wait_timeout_ms": int((scenario_config or {}).get("manual_wait_timeout_ms") or 180000),
                    "username_env": credential_policy["username_env"],
                    "password_env": credential_policy["password_env"],
                    "forbidden_actions": list((scenario_config or {}).get("forbidden_actions") or []),
                }
            )

        return plan

    def _build_prompt(
        self,
        test_case: Dict[str, Any],
        strategy_context: Optional[Dict[str, Any]],
        baseline: ScriptExecutionPlan,
    ) -> str:
        test_case_json = json.dumps(test_case, ensure_ascii=False, indent=2)
        strategy_json = json.dumps(strategy_context or {}, ensure_ascii=False, indent=2)
        baseline_json = json.dumps(baseline.model_dump(), ensure_ascii=False, indent=2)
        return (
            "你是一个测试脚本规划 agent。请基于测试用例、策略上下文和确定性 baseline，"
            "输出一个更优但依然可执行、可审计的 ScriptExecutionPlan。\n"
            "要求：\n"
            "1. 不要删除 testcase_id/title/setup.page_url。\n"
            "2. 只能调整 scenario.execution_policy、steps[*].preferred_executor、action_prompt、verify_prompt、metadata.reasoning_summary、metadata.confidence。\n"
            "3. 如果 baseline 的 native_operations 已足够稳定，不要改成纯 AI。\n"
            "4. 登录、支付、权限、失败恢复等高风险步骤优先保留 native 或 mixed。\n"
            "5. 只输出结构化结果。\n\n"
            f"测试用例:\n{test_case_json}\n\n"
            f"策略上下文:\n{strategy_json}\n\n"
            f"baseline:\n{baseline_json}\n"
        )

    def _merge_plan(self, baseline: ScriptExecutionPlan, llm_plan: ScriptExecutionPlan) -> ScriptExecutionPlan:
        merged_steps = []
        for index, base_step in enumerate(baseline.steps):
            overlay = llm_plan.steps[index] if index < len(llm_plan.steps) else None
            if overlay is None:
                merged_steps.append(base_step)
                continue

            preferred_executor = overlay.preferred_executor
            if preferred_executor == ExecutionTarget.MIDSCENE_AI and base_step.native_operations:
                preferred_executor = ExecutionTarget.MIXED

            merged_steps.append(
                base_step.model_copy(
                    update={
                        "preferred_executor": preferred_executor,
                        "action_prompt": overlay.action_prompt or base_step.action_prompt,
                        "verify_prompt": overlay.verify_prompt or base_step.verify_prompt,
                        "decision_trace": PlannerDecisionTrace(
                            source="llm_overlay",
                            reason=(overlay.decision_trace.reason if overlay.decision_trace else "LLM adjusted step executor"),
                            confidence=(overlay.decision_trace.confidence if overlay.decision_trace else 0.58),
                        ),
                    }
                )
            )

        merged = baseline.model_copy(
            update={
                "scenario": baseline.scenario.model_copy(
                    update={
                        "execution_policy": llm_plan.scenario.execution_policy or baseline.scenario.execution_policy,
                        "allow_ai_only": llm_plan.scenario.allow_ai_only,
                    }
                ),
                "steps": merged_steps,
                "metadata": {
                    **baseline.metadata,
                    "source": "llm_overlay",
                    "reasoning_summary": llm_plan.metadata.get("reasoning_summary")
                    or baseline.metadata.get("reasoning_summary"),
                    "confidence": llm_plan.metadata.get("confidence", baseline.metadata.get("confidence", 0.6)),
                },
            }
        )
        return merged

    def _infer_risk_level(self, strategy_context: Optional[Dict[str, Any]]) -> str:
        requirement_strategy = (strategy_context or {}).get("requirement_strategy") or {}
        return str(requirement_strategy.get("overall_risk") or "medium")

    def _infer_execution_policy(self, execution_mode: str, scenario_type: str) -> ExecutionPolicy:
        if scenario_type == "login_only":
            return ExecutionPolicy.NATIVE_FIRST
        if execution_mode == "smoke":
            return ExecutionPolicy.NATIVE_FIRST
        if execution_mode == "deep":
            return ExecutionPolicy.HYBRID_BALANCED
        return ExecutionPolicy.HYBRID_BALANCED

    def _build_reasoning_summary(
        self,
        test_case: Dict[str, Any],
        strategy_context: Optional[Dict[str, Any]],
        scenario_type: str,
    ) -> str:
        execution_mode = str((strategy_context or {}).get("execution_mode") or "standard")
        return (
            f"Scenario={scenario_type}; execution_mode={execution_mode}; "
            f"step_count={len(test_case.get('steps') or [])}; "
            "prefer deterministic actions for stable fields and mixed verification for semantic checks."
        )
