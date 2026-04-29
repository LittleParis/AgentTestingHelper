"""Validation and normalization for script execution plans."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.automation.script_tools import (
    AssertionStrategyTool,
    CredentialPolicyTool,
    SafetyGuardTool,
    ScenarioClassifierTool,
    SelectorCatalogTool,
)
from core.models.script_plan import ExecutionPolicy, ScriptExecutionPlan
from core.models.script_plan import AssertionIntent, AssertionKind


class PlanValidator:
    """Repair incomplete plans and enforce scenario constraints."""

    def __init__(self):
        self.selector_catalog = SelectorCatalogTool()
        self.credential_policy = CredentialPolicyTool()
        self.assertion_strategy = AssertionStrategyTool()
        self.safety_guard = SafetyGuardTool()
        self.scenario_classifier = ScenarioClassifierTool()

    def validate(
        self,
        plan: ScriptExecutionPlan,
        *,
        scenario_config: Optional[Dict[str, Any]],
        tc_type: str = "functional",
        tc_title: str = "",
        steps: Optional[list[dict[str, Any]]] = None,
    ) -> ScriptExecutionPlan:
        scenario_type = self.scenario_classifier.classify(
            steps or [],
            plan.setup.page_url,
            scenario_config=scenario_config,
            tc_title=tc_title or plan.title,
        )

        plan.scenario.scenario_type = scenario_type
        if not plan.scenario.selectors:
            plan.scenario.selectors = self.selector_catalog.get_catalog(scenario_type)

        credential_policy = self.credential_policy.resolve(
            scenario_type=scenario_type,
            scenario_config=scenario_config,
            tc_type=tc_type,
            tc_title=tc_title or plan.title,
            steps=steps or [],
        )

        if credential_policy["requires_runtime_credentials"]:
            plan.scenario.requires_runtime_credentials = True
            for env_name in credential_policy["required_env_vars"]:
                if env_name not in plan.setup.required_env_vars:
                    plan.setup.required_env_vars.append(env_name)

        if plan.scenario.execution_policy == ExecutionPolicy.AI_FIRST and plan.scenario.requires_runtime_credentials:
            plan.scenario.execution_policy = ExecutionPolicy.HYBRID_BALANCED

        for index, step in enumerate(plan.steps):
            if not step.action_prompt and not step.native_operations:
                step.action_prompt = step.original_action

            if not step.assertion_intents and step.original_expected:
                step.assertion_intents = self.assertion_strategy.build_step_assertions(
                    action=step.original_action,
                    expected=step.original_expected,
                    verify_prompt=step.verify_prompt,
                    data=step.normalized_data,
                    scenario_type=scenario_type,
                )

            if not step.verify_prompt and step.original_expected:
                step.verify_prompt = step.original_expected

            if step.step_number != index + 1:
                step.step_number = index + 1

        if not plan.final_assertions and plan.metadata.get("final_expected"):
            plan.final_assertions = self.assertion_strategy.build_final_assertions(
                expected=str(plan.metadata.get("final_expected") or ""),
                scenario_type=scenario_type,
            )

        if not plan.final_assertions and scenario_type == "login_only":
            success_signal = (scenario_config or {}).get("success_signal") or {}
            success_value = str(success_signal.get("value") or "").strip()
            if success_value:
                plan.final_assertions = [
                    AssertionIntent(kind=AssertionKind.TEXT_VISIBLE, expected_value=success_value)
                ]

        self.safety_guard.apply(
            plan_scenario=plan.scenario,
            plan_setup=plan.setup,
            plan_steps=plan.steps,
            scenario_config=scenario_config,
        )
        return plan
