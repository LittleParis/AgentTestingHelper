"""Composable tools used by script planning and validation."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.models.script_plan import (
    AssertionIntent,
    AssertionKind,
    ExecutionPolicy,
    ExecutionTarget,
    IntentType,
    NativeOperation,
    NativeOperationKind,
    PlannerDecisionTrace,
    ScenarioPlan,
    ScriptSetupPlan,
    ScriptStepPlan,
)


SELECTOR_CATALOG: Dict[str, Dict[str, str]] = {
    "login": {
        "identifierInput": 'input[type="email"]:visible, input[autocomplete="username"]:visible, input[name*="user" i]:visible, input[name*="account" i]:visible, input[name*="mobile" i]:visible, input[name*="phone" i]:visible, input[type="tel"]:visible, input[type="text"]:visible',
        "passwordInput": 'input[type="password"]:visible',
        "submitButton": 'button[type="submit"]:visible, input[type="submit"]:visible, button:visible',
    },
    "search": {
        "searchInput": '#kw:visible, input[name="wd"]:visible, textarea[name="wd"]:visible, input.s_ipt:visible, textarea.s_ipt:visible',
        "searchButton": '#su:visible, input[type="submit"]:visible, button:visible',
    },
    "payment": {
        "amountInput": 'input[placeholder*="金额" i]:visible, input[inputmode="decimal"]:visible, input[name*="amount" i]:visible',
        "submitButton": 'button:has-text("支付"), button:has-text("确认"), button:has-text("提交"), button[type="submit"]:visible',
    },
    "form": {
        "formInput": "input:visible, textarea:visible",
        "submitButton": 'button[type="submit"]:visible, input[type="submit"]:visible, button:visible',
    },
    "generic": {
        "identifierInput": 'input[type="email"]:visible, input[autocomplete="username"]:visible, input[name*="user" i]:visible, input[name*="account" i]:visible, input[name*="mobile" i]:visible, input[name*="phone" i]:visible, input[type="tel"]:visible, input[type="text"]:visible',
        "passwordInput": 'input[type="password"]:visible',
        "submitButton": 'button[type="submit"]:visible, input[type="submit"]:visible, button:visible',
        "searchInput": '#kw:visible, input[name="wd"]:visible, textarea[name="wd"]:visible, input.s_ipt:visible, textarea.s_ipt:visible',
        "searchButton": '#su:visible, input[type="submit"]:visible, button:visible',
    },
}


class SelectorCatalogTool:
    """Provide per-scenario locator catalogs."""

    def get_catalog(self, scenario_type: str) -> Dict[str, str]:
        if scenario_type == "login_only":
            scenario_type = "login"
        return dict(SELECTOR_CATALOG.get(scenario_type, SELECTOR_CATALOG["generic"]))


class ScenarioClassifierTool:
    """Classify a testcase into a coarse scenario bucket."""

    def classify(
        self,
        steps: List[Dict[str, Any]],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
        tc_title: str = "",
    ) -> str:
        config_type = str((scenario_config or {}).get("scenario_type") or "").strip().lower()
        if config_type:
            return config_type if config_type in {"login", "search", "payment", "form", "generic", "login_only"} else "generic"

        url_lower = str(page_url or "").lower()
        if any(keyword in url_lower for keyword in ("login", "signin", "auth", "登录")):
            return "login"
        if any(keyword in url_lower for keyword in ("search", "百度", "google", "bing")):
            return "search"
        if any(keyword in url_lower for keyword in ("pay", "checkout", "订单", "支付")):
            return "payment"

        title_lower = str(tc_title or "").lower()
        if any(keyword in title_lower for keyword in ("登录", "login", "signin", "认证", "验证")):
            return "login"
        if any(keyword in title_lower for keyword in ("搜索", "search", "查询", "检索")):
            return "search"
        if any(keyword in title_lower for keyword in ("支付", "付款", "pay", "checkout", "订单")):
            return "payment"
        if any(keyword in title_lower for keyword in ("表单", "form", "填写", "提交")):
            return "form"

        combined = " ".join(
            str(part).lower()
            for step in steps
            if isinstance(step, dict)
            for part in (step.get("action", ""), step.get("expected", ""))
        )
        if any(keyword in combined for keyword in ("登录", "账号", "账户", "用户名", "password", "username", "signin", "login")):
            return "login"
        if any(keyword in combined for keyword in ("搜索", "查询", "检索", "search", "百度", "google")):
            return "search"
        if any(keyword in combined for keyword in ("支付", "付款", "金额", "pay", "checkout", "amount", "订单")):
            return "payment"
        if any(keyword in combined for keyword in ("表单", "form", "填写", "提交")):
            return "form"
        return "generic"


class CredentialPolicyTool:
    """Resolve runtime credential requirements and negative-login behavior."""

    def resolve(
        self,
        scenario_type: str,
        scenario_config: Optional[Dict[str, Any]],
        tc_type: str,
        tc_title: str,
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        credentials = (scenario_config or {}).get("credentials") or {}
        username_env = str(credentials.get("username_env") or "LOGIN_USERNAME")
        password_env = str(credentials.get("password_env") or "LOGIN_PASSWORD")
        is_negative_test = self._is_negative_login_test(tc_type, tc_title, steps)

        requires_runtime_credentials = scenario_type in {"login", "login_only"}
        use_runtime_password = requires_runtime_credentials and not is_negative_test

        return {
            "username_env": username_env,
            "password_env": password_env,
            "requires_runtime_credentials": requires_runtime_credentials,
            "use_runtime_username": requires_runtime_credentials,
            "use_runtime_password": use_runtime_password,
            "is_negative_test": is_negative_test,
            "required_env_vars": [username_env, password_env] if requires_runtime_credentials else [],
        }

    def _is_negative_login_test(self, tc_type: str, tc_title: str, steps: List[Dict[str, Any]]) -> bool:
        if str(tc_type or "").lower() == "negative":
            return True

        title_lower = str(tc_title or "").lower()
        if any(keyword in title_lower for keyword in ("无效", "错误", "不存在", "失败", "invalid", "wrong", "incorrect", "nonexistent", "failure", "异常")):
            return True

        for step in steps:
            action = str((step or {}).get("action", "")).lower()
            if self._mentions_password_field(action) and any(
                keyword in action for keyword in ("无效", "错误", "wrong", "invalid", "incorrect", "任意", "错误密码")
            ):
                return True
        return False

    def _mentions_password_field(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return "密码" in normalized or "password" in normalized or "secret" in normalized


class ActionStrategyTool:
    """Map natural-language steps into structured execution decisions."""

    def normalize_step_data(self, action: str, data: Any) -> str:
        value = "" if data is None else str(data).strip()
        if not value:
            return ""
        action_text = str(action or "")
        if not any(keyword in action_text for keyword in ("输入", "填写", "input", "fill")):
            return value

        credential_match = re.match(
            r"^\s*(identifier|username|password|用户名|账号|账户|密码)\s*[:：]\s*(.+?)\s*$",
            value,
            re.IGNORECASE,
        )
        if credential_match:
            return credential_match.group(2).strip()
        return value

    def plan_step(
        self,
        *,
        step_number: int,
        action: str,
        data: str,
        expected: str,
        scenario_type: str,
        credential_policy: Dict[str, Any],
        focus_hint: Optional[Dict[str, Any]] = None,
    ) -> ScriptStepPlan:
        action_text = str(action or "")
        expected_text = str(expected or "")
        normalized_data = self.normalize_step_data(action_text, data)
        focus_hint = focus_hint or {}

        preferred_executor = ExecutionTarget.MIXED
        execution_mode = str(focus_hint.get("execution_mode") or "").lower()
        if execution_mode == "smoke":
            preferred_executor = ExecutionTarget.PLAYWRIGHT_NATIVE
        elif execution_mode == "deep":
            preferred_executor = ExecutionTarget.MIXED

        native_operations = self._build_native_operations(
            action_text,
            normalized_data,
            expected_text,
            scenario_type,
            credential_policy,
        )
        action_prompt = self._build_action_prompt(action_text, normalized_data, expected_text)
        intent_type = self._classify_intent(action_text)

        if native_operations and preferred_executor == ExecutionTarget.MIXED:
            preferred_executor = ExecutionTarget.PLAYWRIGHT_NATIVE
        elif not native_operations:
            preferred_executor = ExecutionTarget.MIDSCENE_AI

        return ScriptStepPlan(
            step_number=step_number,
            original_action=action_text,
            original_expected=expected_text,
            normalized_data=normalized_data,
            intent_type=intent_type,
            target=self._infer_target(action_text, scenario_type),
            preferred_executor=preferred_executor,
            action_prompt=action_prompt,
            native_operations=native_operations,
            decision_trace=PlannerDecisionTrace(
                source="action_strategy_tool",
                reason=f"scenario={scenario_type}, execution_mode={execution_mode or 'default'}",
                confidence=0.74 if native_operations else 0.52,
            ),
            metadata={
                "focus_point_id": focus_hint.get("point_id"),
                "focus_level": focus_hint.get("focus_level"),
                "execution_mode": focus_hint.get("execution_mode"),
            },
        )

    def _classify_intent(self, action: str) -> IntentType:
        normalized = str(action or "").lower()
        if any(keyword in normalized for keyword in ("打开", "访问", "进入", "open", "visit", "goto")):
            return IntentType.OPEN_PAGE
        if any(keyword in normalized for keyword in ("输入", "填写", "fill", "input")):
            return IntentType.INPUT
        if any(keyword in normalized for keyword in ("点击", "submit", "click")):
            return IntentType.CLICK
        if any(keyword in normalized for keyword in ("等待", "wait")):
            return IntentType.WAIT
        if any(keyword in normalized for keyword in ("验证", "检查", "确认", "observe", "观察")):
            return IntentType.VERIFY
        return IntentType.GENERIC

    def _infer_target(self, action: str, scenario_type: str) -> str:
        normalized = str(action or "").lower()
        if self._mentions_password_field(normalized):
            return "passwordInput"
        if self._mentions_login_identifier(normalized):
            return "identifierInput"
        if "搜索" in normalized or "search" in normalized:
            return "searchButton" if ("点击" in normalized or "click" in normalized) else "searchInput"
        if "金额" in normalized or "amount" in normalized:
            return "amountInput"
        if scenario_type == "form":
            return "formInput"
        return ""

    def _build_native_operations(
        self,
        action: str,
        data: str,
        expected: str,
        scenario_type: str,
        credential_policy: Dict[str, Any],
    ) -> List[NativeOperation]:
        action_text = str(action or "")
        action_lower = action_text.lower()
        use_runtime_password = bool(credential_policy.get("use_runtime_password"))

        if "清空" in action_text or "清除" in action_text or "clear" in action_lower:
            if self._mentions_password_field(action_text):
                return [NativeOperation(kind=NativeOperationKind.FILL, locator="passwordInput", value="")]
            if self._mentions_login_identifier(action_text):
                return [NativeOperation(kind=NativeOperationKind.FILL, locator="identifierInput", value="")]
            return [NativeOperation(kind=NativeOperationKind.FILL, locator="searchInput", value="")]

        if self._mentions_login_identifier(action_text):
            if self._is_empty_input_action(action_text):
                return [NativeOperation(kind=NativeOperationKind.FILL, locator="identifierInput", value="")]
            return [
                NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="identifierInput"),
                NativeOperation(
                    kind=NativeOperationKind.FILL,
                    locator="identifierInput",
                    runtime_var="runtimeUsername",
                    fallback_value=data or "test",
                ),
            ]

        if self._mentions_password_field(action_text):
            if self._is_empty_input_action(action_text):
                return [NativeOperation(kind=NativeOperationKind.FILL, locator="passwordInput", value="")]
            return [
                NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="passwordInput"),
                NativeOperation(
                    kind=NativeOperationKind.FILL,
                    locator="passwordInput",
                    runtime_var="runtimePassword" if use_runtime_password else None,
                    fallback_value=data if use_runtime_password else (data or "WrongPassword123"),
                ),
            ]

        if self._is_login_submit_action(action_text):
            return [
                NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="submitButton"),
                NativeOperation(kind=NativeOperationKind.CLICK, locator="submitButton"),
            ]

        if scenario_type in {"search", "generic"}:
            if self._is_empty_input_action(action_text):
                return [NativeOperation(kind=NativeOperationKind.FILL, locator="searchInput", value="")]
            if ("输入" in action_text or "可输入" in action_text or "fill" in action_lower or "input" in action_lower) and (
                "搜索" in action_text or "search" in action_lower or "输入框" in action_text
            ):
                return [
                    NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="searchInput"),
                    NativeOperation(kind=NativeOperationKind.FILL, locator="searchInput", value=data or "test"),
                ]
            if ("点击" in action_text or "click" in action_lower) and ("搜索" in action_text or "search" in action_lower):
                return [
                    NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="searchButton"),
                    NativeOperation(kind=NativeOperationKind.CLICK, locator="searchButton"),
                ]

        if any(keyword in action_text for keyword in ("打开", "访问", "导航", "进入", "wait", "等待")):
            return [
                NativeOperation(kind=NativeOperationKind.WAIT_LOAD),
                NativeOperation(kind=NativeOperationKind.WAIT_TIMEOUT, timeout_ms=1000),
            ]

        if scenario_type == "payment" and ("金额" in action_text or "amount" in action_lower):
            return [
                NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="amountInput"),
                NativeOperation(kind=NativeOperationKind.FILL, locator="amountInput", value=data or "100"),
            ]

        if scenario_type == "form" and any(keyword in action_text for keyword in ("输入", "填写", "fill", "input")):
            return [
                NativeOperation(kind=NativeOperationKind.EXPECT_VISIBLE, locator="formInput"),
                NativeOperation(kind=NativeOperationKind.FILL, locator="formInput", value=data or "test"),
            ]

        return []

    def _build_action_prompt(self, action: str, data: str, expected: str) -> str:
        action = str(action or "").strip()
        data = str(data or "").strip()
        expected = str(expected or "").strip()
        if not action:
            return ""
        if data and any(keyword in action for keyword in ("输入", "填写", "input", "fill")):
            if self._mentions_password_field(action):
                return "在密码输入框输入内容"
            if self._mentions_login_identifier(action):
                return f'在用户名输入框输入 "{data}"'
            if "搜索" in action or "search" in action.lower():
                return f'在搜索框输入 "{data}"'
            return f'在输入框输入 "{data}"'
        if any(keyword in action for keyword in ("点击", "click")):
            if "登录" in action:
                return "点击登录按钮"
            if "搜索" in action or "search" in action.lower():
                return "点击搜索按钮"
            if "提交" in action:
                return "点击提交按钮"
            return "点击页面上的按钮"
        if any(keyword in action for keyword in ("观察", "验证", "检查", "确认")) and expected:
            return f"观察页面是否满足: {expected}"
        if any(keyword in action for keyword in ("打开", "访问", "导航", "进入", "wait", "等待")):
            return "等待页面加载完成"
        return action

    def _mentions_login_identifier(self, text: str) -> bool:
        normalized = str(text or "").lower()
        has_identifier = any(
            keyword in normalized
            for keyword in ("账号", "账户", "用户名", "用户标识", "identifier", "username", "account", "email", "mobile", "phone")
        )
        return has_identifier and "密码" not in normalized and "password" not in normalized

    def _mentions_password_field(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return "密码" in normalized or "password" in normalized or "secret" in normalized

    def _is_login_submit_action(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return ("点击" in normalized or "submit" in normalized or "click" in normalized) and any(
            keyword in normalized for keyword in ("登录", "sign in", "signin", "submit")
        )

    def _is_empty_input_action(self, text: str) -> bool:
        normalized = str(text or "")
        return (
            ("保持" in normalized and "空" in normalized)
            or ("清空" in normalized)
            or ("clear" in normalized.lower())
        )


class AssertionStrategyTool:
    """Translate expected results into structured assertion intents."""

    def build_step_assertions(
        self,
        *,
        action: str,
        expected: str,
        verify_prompt: str,
        data: str,
        scenario_type: str,
    ) -> List[AssertionIntent]:
        action_text = str(action or "")
        expected_text = str(expected or "")
        verify_text = str(verify_prompt or "")
        combined = " ".join([action_text, expected_text, verify_text])

        if self._is_same_page_assertion(combined):
            return [AssertionIntent(kind=AssertionKind.URL_SAME)]

        if self._is_url_assertion(verify_text or expected_text):
            intents = [AssertionIntent(kind=AssertionKind.URL_CHANGED)]
            if "搜索参数" in (verify_text or expected_text):
                intents.append(AssertionIntent(kind=AssertionKind.URL_MATCHES, regex="(wd|word)="))
            return intents

        if scenario_type in {"login", "generic"}:
            login_assertions = self._build_login_assertions(combined, data, expected_text)
            if login_assertions:
                return login_assertions

        if scenario_type in {"search", "generic"}:
            search_assertions = self._build_search_assertions(combined, data, expected_text)
            if search_assertions:
                return search_assertions

        if scenario_type == "payment" and any(keyword in combined for keyword in ("金额", "amount", "可见", "visible")):
            return [AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="amountInput")]

        if scenario_type == "form" and any(keyword in combined for keyword in ("表单", "输入", "visible", "可见")):
            return [
                AssertionIntent(kind=AssertionKind.PAGE_BODY_VISIBLE),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="formInput"),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="submitButton"),
            ]

        if expected_text and any(keyword in expected_text for keyword in ("提示", "信息", "错误")):
            return [AssertionIntent(kind=AssertionKind.PAGE_BODY_VISIBLE)]

        return []

    def build_final_assertions(
        self,
        *,
        expected: str,
        scenario_type: str,
    ) -> List[AssertionIntent]:
        expected_text = str(expected or "")
        if not expected_text:
            return []
        return self.build_step_assertions(
            action="Final verify",
            expected=expected_text,
            verify_prompt=expected_text,
            data="",
            scenario_type=scenario_type,
        )

    def _build_login_assertions(self, combined: str, data: str, expected_text: str) -> List[AssertionIntent]:
        if any(keyword in combined for keyword in ("空白", "为空", "保持空", "清空")):
            if self._mentions_password_field(combined):
                return [AssertionIntent(kind=AssertionKind.VALUE_EMPTY, locator="passwordInput")]
            if self._mentions_login_identifier(combined):
                return [AssertionIntent(kind=AssertionKind.VALUE_EMPTY, locator="identifierInput")]

        if self._mentions_password_field(combined) and any(keyword in combined for keyword in ("显示", "输入", "非空")):
            return [AssertionIntent(kind=AssertionKind.VALUE_NONEMPTY, locator="passwordInput")]

        if self._mentions_login_identifier(combined) and any(keyword in combined for keyword in ("显示", "输入")):
            return [
                AssertionIntent(
                    kind=AssertionKind.VALUE_EQUALS,
                    locator="identifierInput",
                    runtime_var="runtimeUsername",
                    expected_value=data or None,
                )
            ]

        if any(keyword in combined for keyword in ("页面", "加载", "可见")) and any(
            keyword in combined for keyword in ("登录", "用户名", "密码", "按钮", "输入框")
        ):
            return [
                AssertionIntent(kind=AssertionKind.PAGE_BODY_VISIBLE),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="identifierInput"),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="passwordInput"),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="submitButton"),
            ]

        return []

    def _build_search_assertions(self, combined: str, data: str, expected_text: str) -> List[AssertionIntent]:
        if any(keyword in combined for keyword in ("空白", "为空", "保持空", "清空")):
            return [AssertionIntent(kind=AssertionKind.VALUE_EMPTY, locator="searchInput")]

        if any(keyword in combined for keyword in ("搜索结果", "结果页", "结果列表")):
            return [
                AssertionIntent(kind=AssertionKind.URL_CHANGED),
                AssertionIntent(kind=AssertionKind.URL_MATCHES, regex="(wd|word|/s\\?)"),
                AssertionIntent(kind=AssertionKind.PAGE_BODY_VISIBLE),
            ]

        if any(keyword in combined for keyword in ("搜索框", "输入框")) and any(keyword in combined for keyword in ("可见", "visible", "存在", "定位")):
            return [AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="searchInput")]

        if any(keyword in combined for keyword in ("搜索框", "输入框")) and any(keyword in combined for keyword in ("显示", "输入")):
            return [
                AssertionIntent(kind=AssertionKind.VALUE_EQUALS, locator="searchInput", expected_value=data or None)
            ]

        if any(keyword in combined for keyword in ("页面", "加载", "可见")) and "按钮" in combined:
            return [
                AssertionIntent(kind=AssertionKind.PAGE_BODY_VISIBLE),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="searchInput"),
                AssertionIntent(kind=AssertionKind.LOCATOR_VISIBLE, locator="searchButton"),
            ]

        return []

    def _is_same_page_assertion(self, combined: str) -> bool:
        return any(keyword in combined for keyword in ("未跳转", "仍停留", "停留在登录页", "URL未变化"))

    def _is_url_assertion(self, text: str) -> bool:
        normalized = str(text or "")
        return "URL" in normalized or "地址栏" in normalized

    def _mentions_login_identifier(self, text: str) -> bool:
        normalized = str(text or "").lower()
        has_identifier = any(
            keyword in normalized
            for keyword in ("账号", "账户", "用户名", "用户标识", "identifier", "username", "account", "email", "mobile", "phone")
        )
        return has_identifier and "密码" not in normalized and "password" not in normalized

    def _mentions_password_field(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return "密码" in normalized or "password" in normalized or "secret" in normalized


class SafetyGuardTool:
    """Apply lightweight safety constraints on generated plans."""

    def apply(
        self,
        *,
        plan_scenario: ScenarioPlan,
        plan_setup: ScriptSetupPlan,
        plan_steps: List[ScriptStepPlan],
        scenario_config: Optional[Dict[str, Any]],
    ) -> None:
        forbidden_actions = list((scenario_config or {}).get("forbidden_actions") or [])
        if forbidden_actions:
            plan_scenario.safety_constraints.extend(
                item for item in forbidden_actions if item not in plan_scenario.safety_constraints
            )
            plan_setup.safety_constraints.extend(
                item for item in forbidden_actions if item not in plan_setup.safety_constraints
            )

        if plan_scenario.scenario_type == "login_only":
            stop_constraint = "stop_after_login_success"
            if stop_constraint not in plan_scenario.safety_constraints:
                plan_scenario.safety_constraints.append(stop_constraint)


class StrategyFocusResolver:
    """Resolve a testcase against requirement-level strategy hints."""

    def resolve_for_test_case(
        self,
        test_case: Dict[str, Any],
        strategy_plan: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        requirement_id = test_case.get("requirement_id")
        if not requirement_id or not strategy_plan:
            return {}

        for strategy in strategy_plan.get("requirement_strategies") or []:
            if strategy.get("requirement_id") == requirement_id:
                focus_points = strategy.get("focus_points") or []
                execution_mode = self._select_execution_mode(test_case, focus_points)
                return {
                    "requirement_strategy": strategy,
                    "execution_mode": execution_mode,
                    "focus_points": focus_points,
                }
        return {}

    def _select_execution_mode(self, test_case: Dict[str, Any], focus_points: List[Dict[str, Any]]) -> str:
        title = str(test_case.get("title") or "").lower()
        combined_steps = " ".join(str(step.get("action", "")) for step in test_case.get("steps") or []).lower()
        for focus_point in focus_points:
            point_text = str(focus_point.get("point_text") or "").lower()
            if point_text and (point_text in title or any(token and token in combined_steps for token in point_text.split()[:4])):
                return str(focus_point.get("execution_mode") or "standard")

        if any(str(point.get("execution_mode") or "").lower() == "deep" for point in focus_points):
            return "deep"
        if any(str(point.get("execution_mode") or "").lower() == "smoke" for point in focus_points):
            return "smoke"
        return "standard"
