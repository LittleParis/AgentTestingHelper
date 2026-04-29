"""
Midscene test script generator.

This module converts generated test cases into Midscene + Playwright scripts.
The generator intentionally uses a hybrid strategy:

- Deterministic UI operations use Playwright directly.
- Perception or semantic checks still use Midscene `ai(...)`.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.automation.script_planning_agent import ScriptPlanningAgent
from core.automation.script_renderer import ScriptRenderer
from core.models.script_plan import ScriptExecutionPlan
from core.utils.project_paths import GENERATED_TESTS_DIR

try:
    from core.utils.llm_client import get_llm_client as _get_llm_client
except Exception:  # pragma: no cover - optional in lightweight environments
    _get_llm_client = None

get_llm_client = _get_llm_client


class ScenarioType(Enum):
    """场景类型枚举"""
    LOGIN = "login"           # 登录场景
    SEARCH = "search"         # 搜索场景
    PAYMENT = "payment"       # 支付场景
    FORM = "form"             # 表单场景
    GENERIC = "generic"       # 通用场景


# 场景选择器配置
SCENARIO_SELECTORS = {
    ScenarioType.LOGIN: {
        "identifier": "input[type=\"email\"]:visible, input[autocomplete=\"username\"]:visible, input[name*=\"user\" i]:visible, input[name*=\"account\" i]:visible, input[name*=\"mobile\" i]:visible, input[name*=\"phone\" i]:visible, input[type=\"tel\"]:visible, input[type=\"text\"]:visible",
        "password": "input[type=\"password\"]:visible",
        "submit": "button[type=\"submit\"]:visible, input[type=\"submit\"]:visible, button:visible",
    },
    ScenarioType.SEARCH: {
        "input": "#kw:visible, input[name=\"wd\"]:visible, textarea[name=\"wd\"]:visible, input.s_ipt:visible, textarea.s_ipt:visible",
        "submit": "#su:visible, input[type=\"submit\"]:visible, button:visible",
    },
    ScenarioType.PAYMENT: {
        "amount": "input[placeholder*=\"金额\" i]:visible, input[inputmode=\"decimal\"]:visible, input[name*=\"amount\" i]:visible",
        "submit": "button:has-text(\"支付\"), button:has-text(\"确认\"), button:has-text(\"提交\"), button[type=\"submit\"]:visible",
    },
    ScenarioType.FORM: {
        "input": "input:visible, textarea:visible",
        "submit": "button[type=\"submit\"]:visible, input[type=\"submit\"]:visible, button:visible",
    },
    ScenarioType.GENERIC: {
        "input": "input:visible, textarea:visible",
        "submit": "button:visible, input[type=\"submit\"]:visible",
    },
}


class ActionConversionResult(BaseModel):
    """Structured result returned by the LLM step converter."""

    steps: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Converted Midscene steps with action_prompt and verify_prompt.",
    )


class MidsceneScriptGenerator:
    """Generate Midscene + Playwright test scripts."""

    def __init__(self, output_dir: str = str(GENERATED_TESTS_DIR), use_llm: bool = True):
        self.output_dir = output_dir
        self.use_llm = use_llm
        self._llm_client = None
        self._planning_agent = ScriptPlanningAgent(use_llm=use_llm)
        self._renderer = ScriptRenderer()
        os.makedirs(output_dir, exist_ok=True)

    @property
    def llm_client(self):
        if self._llm_client is None and self.use_llm:
            if get_llm_client is None:
                return None
            self._llm_client = get_llm_client()
        return self._llm_client

    def _detect_scenario_type(
        self,
        steps: List[Dict],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
        tc_title: str = "",
    ) -> ScenarioType:
        """检测测试场景类型

        优先级：
        1. 从配置获取
        2. 从 URL 判断
        3. 从测试标题判断
        4. 从步骤内容判断
        5. 默认返回 GENERIC
        """
        # 1. 从配置获取
        if scenario_config:
            config_type = scenario_config.get("scenario_type")
            if config_type:
                try:
                    return ScenarioType(config_type)
                except ValueError:
                    pass

        # 2. 从 URL 判断
        url_lower = str(page_url or "").lower()
        if any(kw in url_lower for kw in ("login", "signin", "auth", "登录")):
            return ScenarioType.LOGIN
        if any(kw in url_lower for kw in ("search", "百度", "google", "bing")):
            return ScenarioType.SEARCH
        if any(kw in url_lower for kw in ("pay", "checkout", "订单", "支付")):
            return ScenarioType.PAYMENT

        # 3. 从测试标题判断
        title_lower = str(tc_title or "").lower()
        if any(kw in title_lower for kw in ("登录", "login", "signin", "认证", "验证")):
            return ScenarioType.LOGIN
        if any(kw in title_lower for kw in ("搜索", "search", "查询", "检索")):
            return ScenarioType.SEARCH
        if any(kw in title_lower for kw in ("支付", "付款", "pay", "checkout", "订单")):
            return ScenarioType.PAYMENT
        if any(kw in title_lower for kw in ("表单", "form", "填写", "提交")):
            return ScenarioType.FORM

        # 4. 从步骤内容判断
        all_actions = " ".join(
            str(step.get("action", "")) for step in steps if isinstance(step, dict)
        ).lower()
        all_expected = " ".join(
            str(step.get("expected", "")) for step in steps if isinstance(step, dict)
        ).lower()
        combined = all_actions + " " + all_expected

        login_keywords = ("登录", "账号", "用户名", "密码", "login", "signin", "password", "username")
        search_keywords = ("搜索", "查询", "检索", "search", "百度", "google")
        payment_keywords = ("支付", "付款", "金额", "pay", "checkout", "amount", "订单")
        form_keywords = ("表单", "填写", "提交", "form", "submit")

        if any(kw in combined for kw in login_keywords):
            return ScenarioType.LOGIN
        if any(kw in combined for kw in search_keywords):
            return ScenarioType.SEARCH
        if any(kw in combined for kw in payment_keywords):
            return ScenarioType.PAYMENT
        if any(kw in combined for kw in form_keywords):
            return ScenarioType.FORM

        # 5. 默认返回通用场景
        return ScenarioType.GENERIC

    def generate(
        self,
        test_cases: List[Dict],
        page_url: str = "https://example.com",
        scenario_config: Optional[Dict[str, Any]] = None,
        strategy_plan: Optional[Dict[str, Any]] = None,
        script_plans: Optional[List[Dict[str, Any]] | List[ScriptExecutionPlan]] = None,
    ) -> str:
        script_content = self._generate_script_content(
            test_cases,
            page_url,
            scenario_config=scenario_config,
            strategy_plan=strategy_plan,
            script_plans=script_plans,
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auto_generated_{timestamp}.spec.ts"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script_content)
        return filepath

    def generate_from_json_file(
        self,
        json_path: str,
        page_url: str = "https://example.com",
        scenario_config: Optional[Dict[str, Any]] = None,
        strategy_plan: Optional[Dict[str, Any]] = None,
    ) -> str:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.generate(
            data.get("test_cases", []),
            page_url,
            scenario_config=scenario_config,
            strategy_plan=strategy_plan,
        )

    def plan_script_generation(
        self,
        test_cases: List[Dict],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
        strategy_plan: Optional[Dict[str, Any]] = None,
    ) -> List[ScriptExecutionPlan]:
        if self._is_login_only_scenario(scenario_config):
            bounded_cases = test_cases[:1] if test_cases else []
            return self._planning_agent.plan_many(
                bounded_cases,
                strategy_plan=strategy_plan,
                scenario_config=scenario_config,
                page_url=page_url,
            )

        return self._planning_agent.plan_many(
            test_cases,
            strategy_plan=strategy_plan,
            scenario_config=scenario_config,
            page_url=page_url,
        )

    def _generate_script_content(
        self,
        test_cases: List[Dict],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
        strategy_plan: Optional[Dict[str, Any]] = None,
        script_plans: Optional[List[Dict[str, Any]] | List[ScriptExecutionPlan]] = None,
    ) -> str:
        if strategy_plan is None and script_plans is None:
            parts = [
                self._generate_header(),
                self._generate_imports(),
                self._generate_test_fixture(),
                "",
                self._generate_test_describe(
                    test_cases,
                    page_url,
                    scenario_config=scenario_config,
                ),
            ]
            return "\n".join(parts)

        resolved_plans = self._coerce_script_plans(
            script_plans,
            test_cases=test_cases,
            page_url=page_url,
            scenario_config=scenario_config,
            strategy_plan=strategy_plan,
        )
        return self._renderer.render(resolved_plans)

    def _coerce_script_plans(
        self,
        script_plans: Optional[List[Dict[str, Any]] | List[ScriptExecutionPlan]],
        *,
        test_cases: List[Dict],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]],
        strategy_plan: Optional[Dict[str, Any]],
    ) -> List[ScriptExecutionPlan]:
        if script_plans:
            return [
                plan if isinstance(plan, ScriptExecutionPlan) else ScriptExecutionPlan.model_validate(plan)
                for plan in script_plans
            ]
        return self.plan_script_generation(
            test_cases,
            page_url=page_url,
            scenario_config=scenario_config,
            strategy_plan=strategy_plan,
        )

    def _generate_header(self) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""/**
 * 自动生成的 Midscene 测试脚本
 *
 * 生成时间: {timestamp}
 * 生成器: MidsceneScriptGenerator
 *
 * 注意: 此文件由程序自动生成，请勿手动修改
 */"""

    def _generate_imports(self) -> str:
        return """import { test as base, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
import allure from 'allure-playwright';"""

    def _generate_test_fixture(self) -> str:
        return """
// 扩展 test 以使用 Midscene AI fixture
const test = base.extend<{
  ai: any;
  aiAction: any;
  aiTap: any;
  aiInput: any;
  aiAssert: any;
  aiQuery: any;
}>(PlaywrightAiFixture());

async function attachStepScreenshot(page: any, stepName: string, testInfo: any) {
  try {
    const screenshot = await page.screenshot({ fullPage: true });
    await testInfo.attach(stepName, { body: screenshot, contentType: 'image/png' });
    console.log(`[SCREENSHOT] ${stepName} 已保存`);
  } catch (error) {
    console.warn(`[SCREENSHOT] Failed: ${stepName}`, error);
  }
}

async function attachFinalScreenshot(page: any, testInfo: any, options: { mask?: any[] } = {}) {
  try {
    const safeStatus = testInfo.status || 'unknown';
    const screenshotPath = testInfo.outputPath(`final-${safeStatus}.png`);
    await page.screenshot({
      path: screenshotPath,
      fullPage: true,
      ...(options.mask ? { mask: options.mask } : {}),
    });
    await testInfo.attach(`final-screenshot-${safeStatus}`, {
      path: screenshotPath,
      contentType: 'image/png',
    });
  } catch (error) {
    console.warn('[SCREENSHOT] Failed to attach final screenshot', error);
  }
}"""

    def _generate_test_describe(
        self,
        test_cases: List[Dict],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        if self._is_login_only_scenario(scenario_config):
            test_functions = [
                self._generate_login_only_test_function(
                    test_cases,
                    page_url,
                    scenario_config or {},
                )
            ]
        else:
            test_functions = [
                self._generate_test_function(
                    tc,
                    page_url,
                    scenario_config=scenario_config,
                )
                for tc in test_cases
            ]
        return "test.describe('自动生成的测试用例', () => {\n" + "\n\n".join(test_functions) + "\n});"

    def _generate_test_function(
        self,
        test_case: Dict,
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        tc_id = test_case.get("id", "TC_XXX")
        title = test_case.get("title", "未命名测试")
        steps = test_case.get("steps", [])
        expected = test_case.get("expected", "")
        tags = test_case.get("tags", [])
        priority = test_case.get("priority", "medium")
        tc_type = test_case.get("type", "functional")

        tag_comment = f"标签: {', '.join(tags)}" if tags else ""
        body = self._generate_test_steps(
            steps,
            page_url,
            expected,
            scenario_config=scenario_config,
            tc_type=tc_type,
            tc_title=title,
        )
        return f"""  test({self._to_ts_string(f"{tc_id}: {title}")}, async ({{ page, ai }}, testInfo) => {{
    // 优先级: {priority}
    // {tag_comment}
    console.log({self._to_ts_string(f"[TEST-START] {tc_id}: {title}")});
    try {{
{body}
    }} finally {{
      await attachFinalScreenshot(page, testInfo);
    }}
    console.log({self._to_ts_string(f"[TEST-END] {tc_id}: {title}")});
  }});"""

    def _is_login_only_scenario(self, scenario_config: Optional[Dict[str, Any]]) -> bool:
        """Return whether the script should use the restricted login template."""
        return (scenario_config or {}).get("scenario_type") == "login_only"

    def _generate_login_only_test_function(
        self,
        test_cases: List[Dict],
        page_url: str,
        scenario_config: Dict[str, Any],
    ) -> str:
        """Generate a single bounded login test that stops after success detection."""
        source_case = test_cases[0] if test_cases else {}
        tc_id = source_case.get("id", "TC_LOGIN_ONLY")
        title = source_case.get("title", "Restricted login verification")
        signal = scenario_config.get("success_signal") or {}
        credentials = scenario_config.get("credentials") or {}
        success_value = str(signal.get("value") or "LianLian")
        success_type = str(signal.get("type") or "visual_text_or_logo")
        manual_wait_timeout_ms = int(scenario_config.get("manual_wait_timeout_ms") or 180000)
        username_env = str(credentials.get("username_env") or "LOGIN_USERNAME")
        password_env = str(credentials.get("password_env") or "LOGIN_PASSWORD")
        forbidden_actions = scenario_config.get("forbidden_actions") or []
        forbidden_comment = ", ".join(forbidden_actions) if forbidden_actions else "none"
        body = self._generate_login_only_steps(
            page_url=page_url,
            success_value=success_value,
            success_type=success_type,
            manual_wait_timeout_ms=manual_wait_timeout_ms,
            username_env=username_env,
            password_env=password_env,
        )
        return f"""  test({self._to_ts_string(f"{tc_id}: {title}")}, async ({{ page, ai }}, testInfo) => {{
    // scenario_type: login_only
    // forbidden_actions: {forbidden_comment}
    console.log({self._to_ts_string(f"[TEST-START] {tc_id}: {title}")});
    let maskedFields = [];
    try {{
{body}
    }} finally {{
      await attachFinalScreenshot(page, testInfo, {{ mask: maskedFields }});
    }}
    console.log({self._to_ts_string(f"[TEST-END] {tc_id}: {title}")});
  }});"""

    def _generate_login_only_steps(
        self,
        page_url: str,
        success_value: str,
        success_type: str,
        manual_wait_timeout_ms: int,
        username_env: str,
        password_env: str,
    ) -> str:
        """Generate a safe login-only flow using runtime environment credentials."""
        success_logo_selector = self._build_success_logo_selector(success_value, success_type)
        return "\n".join(
            [
                f"    const loginUsername = process.env[{self._to_ts_string(username_env)}];",
                f"    const loginPassword = process.env[{self._to_ts_string(password_env)}];",
                "    if (!loginUsername || !loginPassword) {",
                f"      throw new Error('Missing login credentials. Add identifier/password to the requirement file, or configure {username_env}/{password_env} in .env.');",
                "    }",
                "    const identifierInput = page.locator(" + self._to_ts_string(
                    "input[type=\"email\"]:visible, input[autocomplete=\"username\"]:visible, input[name*=\"user\" i]:visible, input[name*=\"account\" i]:visible, input[name*=\"mobile\" i]:visible, input[name*=\"phone\" i]:visible, input[type=\"text\"]:visible"
                ) + ").first();",
                "    const passwordInput = page.locator('input[type=\"password\"]:visible').first();",
                "    const submitButton = page.locator(" + self._to_ts_string(
                    "button[type=\"submit\"]:visible, input[type=\"submit\"]:visible, button:visible"
                ) + ").first();",
                f"    const successText = page.getByText({self._to_ts_string(success_value)}, {{ exact: false }});",
                f"    const successLogo = page.locator({self._to_ts_string(success_logo_selector)}).first();",
                "    const successSignal = successLogo.or(successText).first();",
                "    maskedFields = [identifierInput, passwordInput];",
                "    console.log('[STEP] Open login page');",
                f"    await page.goto({self._to_ts_string(page_url)});",
                "    await page.waitForLoadState('domcontentloaded');",
                "    await expect(identifierInput).toBeVisible();",
                "    await expect(passwordInput).toBeVisible();",
                "    console.log('[STEP] Fill login identifier');",
                "    await identifierInput.fill(loginUsername);",
                "    console.log('[STEP] Fill login secret');",
                "    await passwordInput.fill(loginPassword);",
                "    console.log('[STEP] Capture masked login screenshot');",
                "    await page.screenshot({ path: 'test-results/login-only-before-submit.png', mask: maskedFields });",
                "    console.log('[STEP] Submit login form');",
                "    await expect(submitButton).toBeVisible();",
                "    await submitButton.click();",
                "    console.log('[MANUAL-WAIT] Waiting for manual verification to complete.');",
                "    await page.waitForLoadState('domcontentloaded');",
                f"    await expect(successSignal).toBeVisible({{ timeout: {manual_wait_timeout_ms} }});",
                "    console.log('[VERIFY] Login success signal detected.');",
                "    await page.screenshot({ path: 'test-results/login-only-success.png' });",
                "    await expect(successSignal).toBeVisible();",
                "    // Stop immediately after login success detection. No further actions are allowed.",
            ]
        )

    def _build_success_logo_selector(self, success_value: str, success_type: str) -> str:
        """Build a safe Playwright logo selector for a login success signal."""
        escaped = success_value.replace("\\", "\\\\").replace("\"", "\\\"")
        if success_type == "visual_text_or_logo":
            return (
                f"img[alt*=\"{escaped}\" i], "
                f"[aria-label*=\"{escaped}\" i], "
                f"[title*=\"{escaped}\" i], "
                f"img[src*=\"{escaped.lower()}\" i]"
            )
        return f"[aria-label*=\"{escaped}\" i], [title*=\"{escaped}\" i]"

    def _generate_test_steps(
        self,
        steps: List[Dict],
        page_url: str,
        final_expected: str,
        scenario_config: Optional[Dict[str, Any]] = None,
        tc_type: str = "functional",
        tc_title: str = "",
    ) -> str:
        username_env, password_env = self._get_runtime_credential_env_names(scenario_config)
        is_negative_test = self._is_negative_login_test(tc_type, tc_title, steps)

        # 检测场景类型
        scenario_type = self._detect_scenario_type(steps, page_url, scenario_config, tc_title)
        selectors = SCENARIO_SELECTORS.get(scenario_type, SCENARIO_SELECTORS[ScenarioType.GENERIC])

        # 根据场景类型生成选择器
        lines = [
            "    // Open target page",
            f"    // Detected scenario type: {scenario_type.value}",
            "    console.log('[STEP] Open target page');",
            f"    await page.goto({self._to_ts_string(page_url)});",
            "    await page.waitForLoadState('domcontentloaded');",
            "    await page.waitForTimeout(1500);",
            "    const initialUrl = page.url();",
            f"    const runtimeUsername = process.env[{self._to_ts_string(username_env)}] ?? '';",
            f"    const runtimePassword = process.env[{self._to_ts_string(password_env)}] ?? '';",
        ]

        # 根据场景类型添加对应的选择器
        if scenario_type == ScenarioType.LOGIN:
            lines.append("    const identifierInput = page.locator(" + self._to_ts_string(selectors["identifier"]) + ").first();")
            lines.append("    const passwordInput = page.locator(" + self._to_ts_string(selectors["password"]) + ").first();")
            lines.append("    const submitButton = page.locator(" + self._to_ts_string(selectors["submit"]) + ").first();")
        elif scenario_type == ScenarioType.SEARCH:
            lines.append("    const searchInput = page.locator(" + self._to_ts_string(selectors["input"]) + ").first();")
            lines.append("    const searchButton = page.locator(" + self._to_ts_string(selectors["submit"]) + ").first();")
            lines.append("    const genericVisibleInput = page.locator(" + self._to_ts_string("input:visible, textarea:visible") + ").first();")
        elif scenario_type == ScenarioType.PAYMENT:
            lines.append("    const amountInput = page.locator(" + self._to_ts_string(selectors["amount"]) + ").first();")
            lines.append("    const submitButton = page.locator(" + self._to_ts_string(selectors["submit"]) + ").first();")
        elif scenario_type == ScenarioType.FORM:
            lines.append("    const formInput = page.locator(" + self._to_ts_string(selectors["input"]) + ").first();")
            lines.append("    const submitButton = page.locator(" + self._to_ts_string(selectors["submit"]) + ").first();")
        else:  # GENERIC - 同时定义常用选择器作为备用
            lines.append("    const identifierInput = page.locator(" + self._to_ts_string(SCENARIO_SELECTORS[ScenarioType.LOGIN]["identifier"]) + ").first();")
            lines.append("    const passwordInput = page.locator(" + self._to_ts_string(SCENARIO_SELECTORS[ScenarioType.LOGIN]["password"]) + ").first();")
            lines.append("    const submitButton = page.locator(" + self._to_ts_string(SCENARIO_SELECTORS[ScenarioType.LOGIN]["submit"]) + ").first();")
            lines.append("    const searchInput = page.locator(" + self._to_ts_string(SCENARIO_SELECTORS[ScenarioType.SEARCH]["input"]) + ").first();")
            lines.append("    const searchButton = page.locator(" + self._to_ts_string(SCENARIO_SELECTORS[ScenarioType.SEARCH]["submit"]) + ").first();")

        lines.extend([
            "",
            "    await attachStepScreenshot(page, '01-initial-page', testInfo);",
            "",
        ])

        converted_steps = self._convert_steps_with_llm(steps) if self.use_llm and self.llm_client and steps else self._fallback_convert_steps(steps)

        for idx, step in enumerate(converted_steps):
            original_action = step.get("original_action", "")
            action_prompt = step.get("action_prompt", "")
            verify_prompt = step.get("verify_prompt", "")
            expected_text = step.get("expected_text", "")
            data = self._normalize_step_data(original_action, step.get("data", ""))

            step_num = idx + 2
            step_desc = original_action[:15] if len(original_action) > 15 else original_action
            screenshot_name = f"{step_num:02d}-{step_desc}"

            lines.append(f"    // Step: {original_action}")
            lines.append(f"    console.log({self._to_ts_string('[STEP] ' + original_action)});")

            native_action_lines = self._generate_native_action_lines(
                original_action, data, expected_text,
                use_runtime_password=not is_negative_test
            )
            if native_action_lines:
                lines.extend(native_action_lines)
            else:
                # Only call ai() if we have a meaningful prompt
                fallback_action = self._convert_action_fallback(original_action, data, expected_text)
                actual_prompt = action_prompt or fallback_action
                if actual_prompt and not self._is_placeholder_prompt(actual_prompt):
                    lines.append(f"    await ai({self._to_ts_string(actual_prompt)});")

            if verify_prompt:
                lines.append(f"    console.log({self._to_ts_string('[VERIFY] ' + (expected_text or verify_prompt))});")
                native_verify_lines = self._generate_native_verify_lines(original_action, data, expected_text, verify_prompt, scenario_type)
                if native_verify_lines:
                    lines.extend(native_verify_lines)
                else:
                    # Only call ai() if verify_prompt is meaningful
                    if verify_prompt and not self._is_placeholder_prompt(verify_prompt):
                        lines.append(f"    await ai({self._to_ts_string('Verify: ' + verify_prompt)});")

            lines.append(f"    await attachStepScreenshot(page, {self._to_ts_string(screenshot_name)}, testInfo);")
            lines.append("")

        final_verify = self._convert_expected_fallback(final_expected)
        if final_verify:
            lines.append("    // Final verify")
            lines.append(f"    console.log({self._to_ts_string('[FINAL-VERIFY] ' + final_expected)});")
            native_final_lines = self._generate_native_verify_lines("Final verify", "", final_expected, final_verify, scenario_type)
            if native_final_lines:
                lines.extend(native_final_lines)
            else:
                lines.append(f"    await ai({self._to_ts_string('Verify: ' + final_verify)});")
            lines.append("    await attachStepScreenshot(page, 'final-verify', testInfo);")

        return "\n".join(lines)

    def _convert_steps_with_llm(self, steps: List[Dict]) -> List[Dict]:
        steps_desc = []
        for i, step in enumerate(steps, 1):
            action = step.get("action", "") if isinstance(step, dict) else str(step)
            data = self._normalize_step_data(action, step.get("data", "") if isinstance(step, dict) else "")
            expected = step.get("expected", "") if isinstance(step, dict) else ""
            steps_desc.append(f"{i}. 操作: {action}；数据: {data}；预期: {expected}")

        prompt = (
            "你是测试自动化专家，需要把测试步骤转换成 Midscene AI 能稳定执行的指令。\n\n"
            "要求：\n"
            "1. action_prompt 必须是可直接执行的自然语言动作，不能为空。\n"
            "2. 避免输出模糊动作，例如“继续下一步”“等待页面跳转或提示信息”。\n"
            "3. verify_prompt 必须是可直接验证的结果描述；没有合适验证时可以留空。\n"
            "4. 只输出 JSON，不要解释。\n\n"
            "输出格式：\n"
            '{\n  "steps": [\n    {"action_prompt": "...", "verify_prompt": "..."}\n  ]\n}\n\n'
            "待转换步骤：\n"
            + "\n".join(steps_desc)
        )

        try:
            result = self.llm_client.invoke_structured(
                ActionConversionResult,
                prompt,
                operation="midscene_action_conversion",
            )
            if not isinstance(result, ActionConversionResult):
                raise ValueError(f"Expected ActionConversionResult, got {type(result).__name__}")

            converted = []
            for i, step in enumerate(steps):
                action = step.get("action", "") if isinstance(step, dict) else str(step)
                data = self._normalize_step_data(action, step.get("data", "") if isinstance(step, dict) else "")
                expected = step.get("expected", "") if isinstance(step, dict) else ""
                raw_action = result.steps[i].get("action_prompt", "") if i < len(result.steps) else ""
                raw_verify = result.steps[i].get("verify_prompt", "") if i < len(result.steps) else ""
                converted.append(
                    {
                        "original_action": action,
                        "action_prompt": self._normalize_action_prompt(action, data, expected, raw_action),
                        "verify_prompt": self._normalize_verify_prompt(expected, raw_verify),
                        "expected_text": expected,
                        "data": data,
                    }
                )
            return converted
        except Exception as e:
            print(f"[WARNING] LLM 转换失败，使用降级方案: {e}")
            return self._fallback_convert_steps(steps)

    def _fallback_convert_steps(self, steps: List[Dict]) -> List[Dict]:
        converted = []
        for step in steps:
            action = step.get("action", "") if isinstance(step, dict) else str(step)
            data = self._normalize_step_data(action, step.get("data", "") if isinstance(step, dict) else "")
            expected = step.get("expected", "") if isinstance(step, dict) else ""
            converted.append(
                {
                    "original_action": action,
                    "action_prompt": self._convert_action_fallback(action, data, expected),
                    "verify_prompt": self._convert_expected_fallback(expected),
                    "expected_text": expected,
                    "data": data,
                }
            )
        return converted

    def _normalize_step_data(self, action: str, data: Any) -> str:
        """Normalize input-like step data so login credentials are filled as raw values."""
        value = "" if data is None else str(data).strip()
        if not value:
            return ""

        action_text = str(action or "")
        if not any(keyword in action_text for keyword in ("输入", "填写")):
            return value

        credential_match = re.match(
            r"^\s*(identifier|username|password|用户名|账号|账户|密码)\s*[:：]\s*(.+?)\s*$",
            value,
            re.IGNORECASE,
        )
        if credential_match:
            return credential_match.group(2).strip()

        return value

    def _get_runtime_credential_env_names(
        self,
        scenario_config: Optional[Dict[str, Any]],
    ) -> tuple[str, str]:
        credentials = (scenario_config or {}).get("credentials") or {}
        username_env = str(credentials.get("username_env") or "LOGIN_USERNAME")
        password_env = str(credentials.get("password_env") or "LOGIN_PASSWORD")
        return username_env, password_env

    def _generate_native_action_lines(self, action: str, data: str, expected: str, use_runtime_password: bool = True) -> List[str]:
        """Generate native Playwright action lines for common operations.

        Returns empty list if the action should be handled by ai() or is too vague.
        """
        action_text = str(action or "")
        data_text = "" if data is None else str(data)
        expected_text = str(expected or "")

        # Clear input operations - check BEFORE input operations
        if "清空" in action_text or "清除" in action_text or "clear" in action_text.lower():
            if self._mentions_password_field(action_text):
                return ["    await passwordInput.fill('');"]
            if self._mentions_login_identifier(action_text):
                return ["    await identifierInput.fill('');"]
            return ["    await searchInput.fill('');"]

        # Login identifier input
        if self._mentions_login_identifier(action_text):
            if self._is_empty_input_action(action_text):
                return ["    await identifierInput.fill('');"]
            value_expr = self._build_runtime_fill_expression("runtimeUsername", data_text)
            return [
                "    await expect(identifierInput).toBeVisible();",
                f"    await identifierInput.fill({value_expr});",
            ]

        # Password input
        if self._mentions_password_field(action_text):
            if self._is_empty_input_action(action_text):
                return ["    await passwordInput.fill('');"]
            if use_runtime_password:
                value_expr = self._build_runtime_fill_expression("runtimePassword", data_text, fallback_literal="")
            else:
                value_expr = self._to_ts_string(data_text) if data_text else '"WrongPassword123"'
            return [
                "    await expect(passwordInput).toBeVisible();",
                f"    await passwordInput.fill({value_expr});",
            ]

        # Login submit button
        if self._is_login_submit_action(action_text):
            return [
                "    await expect(submitButton).toBeVisible();",
                "    await submitButton.click();",
            ]

        # Search input operations
        if "定位" in action_text and ("搜索框" in action_text or "输入框" in action_text):
            return ["    await expect(searchInput).toBeVisible();"]

        if self._is_empty_input_action(action_text):
            return ["    await searchInput.fill('');"]

        if ("输入" in action_text or "可输入" in action_text) and ("搜索框" in action_text or "输入框" in action_text):
            return [f"    await searchInput.fill({self._to_ts_string(data_text or 'test')});"]

        if "点击" in action_text and ("搜索" in action_text or "百度一下" in action_text):
            return [
                "    await expect(searchButton).toBeVisible();",
                "    await searchButton.click();",
            ]

        # Page navigation and loading
        if any(kw in action_text for kw in ("打开", "访问", "导航", "进入")):
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await page.waitForTimeout(1000);",
            ]

        # Wait actions
        if "等待" in action_text:
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await page.waitForTimeout(1000);",
            ]

        # Search result page
        if "搜索结果页" in action_text or "结果页面" in action_text or "结果页" in action_text:
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await page.waitForTimeout(1500);",
            ]

        # Check/verify actions - return empty to trigger native assertions
        if any(kw in action_text for kw in ("检查", "验证", "确认", "观察")):
            return []

        # Page behavior observation
        if "观察页面行为" in action_text and ("提示" in expected_text or "不跳转" in expected_text or "空" in expected_text):
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await page.waitForTimeout(1200);",
            ]

        # Return empty for unhandled actions - they will use ai() if a prompt is available
        return []

    def _generate_native_verify_lines(
        self,
        action: str,
        data: str,
        expected: str,
        verify_prompt: str,
        scenario_type: ScenarioType = ScenarioType.GENERIC,
    ) -> List[str]:
        """生成原生验证代码

        Args:
            action: 动作描述
            data: 数据
            expected: 预期结果
            verify_prompt: 验证提示
            scenario_type: 场景类型，用于决定是否生成原生断言

        Returns:
            原生验证代码列表，空列表表示应使用 ai() 语义验证
        """
        action_text = str(action or "")
        expected_text = str(expected or "")
        verify_text = str(verify_prompt or "")
        data_text = "" if data is None else str(data)
        combined_text = " ".join([action_text, expected_text, verify_text])

        # 通用断言：页面URL不变
        if self._is_same_page_assertion(action_text, expected_text, verify_text):
            return ["    await expect.poll(() => page.url()).toBe(initialUrl);"]

        # 通用断言：URL变化
        if self._is_url_assertion(verify_text):
            return self._generate_native_url_assertions(verify_text)

        # 根据场景类型生成特定断言
        if scenario_type == ScenarioType.LOGIN:
            return self._generate_login_verify_lines(action_text, expected_text, verify_text, data_text, combined_text)
        elif scenario_type == ScenarioType.SEARCH:
            return self._generate_search_verify_lines(action_text, expected_text, verify_text, data_text, combined_text)
        elif scenario_type == ScenarioType.PAYMENT:
            return self._generate_payment_verify_lines(action_text, expected_text, verify_text, data_text, combined_text)
        elif scenario_type == ScenarioType.FORM:
            return self._generate_form_verify_lines(action_text, expected_text, verify_text, data_text, combined_text)
        else:
            # GENERIC 场景：根据内容推断
            lowered = combined_text.lower()
            if (
                "搜索" in combined_text
                or "search" in lowered
                or "输入框" in combined_text
                or "提示信息" in combined_text
                or "不跳转" in combined_text
            ):
                return self._generate_search_verify_lines(action_text, expected_text, verify_text, data_text, combined_text)
            return self._generate_generic_verify_lines(action_text, expected_text, verify_text, data_text, combined_text)

    def _generate_login_verify_lines(
        self,
        action_text: str,
        expected_text: str,
        verify_text: str,
        data_text: str,
        combined_text: str,
    ) -> List[str]:
        """生成登录场景的验证代码"""
        # 清空操作后的验证 - 值应为空
        if "清空" in action_text or "清除" in action_text or "清空" in expected_text:
            if self._mentions_password_field(combined_text):
                return ["    await expect(passwordInput).toHaveValue('');"]
            if self._mentions_login_identifier(combined_text):
                return ["    await expect(identifierInput).toHaveValue('');"]

        # 空输入断言
        if self._is_blank_input_assertion(action_text, expected_text, verify_text):
            if self._mentions_password_field(combined_text):
                return ["    await expect(passwordInput).toHaveValue('');"]
            if self._mentions_login_identifier(combined_text):
                return ["    await expect(identifierInput).toHaveValue('');"]

        # 表单可见性断言
        if self._is_page_form_visibility_assertion(action_text, expected_text, verify_text):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(identifierInput).toBeVisible();",
                "    await expect(passwordInput).toBeVisible();",
                "    await expect(submitButton).toBeVisible();",
            ]

        # 提示/不跳转断言
        if ("提示" in expected_text or "不跳转" in expected_text or "空输入" in expected_text) and (
            "页面行为" in action_text or "系统行为" in action_text or "空" in expected_text
        ):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(identifierInput).toBeVisible();",
                "    await expect(passwordInput).toBeVisible();",
                "    await expect(submitButton).toBeVisible();",
            ]

        # 密码字段可见性
        if self._mentions_password_field(combined_text) and any(keyword in combined_text for keyword in ("可见", "存在", "定位")):
            if self._is_error_message_expected(expected_text, verify_text):
                return []
            return ["    await expect(passwordInput).toBeVisible();"]

        # 标识符字段可见性
        if self._mentions_login_identifier(combined_text) and any(keyword in combined_text for keyword in ("可见", "存在", "定位")):
            if self._is_error_message_expected(expected_text, verify_text):
                return []
            return ["    await expect(identifierInput).toBeVisible();"]

        # 密码字段值
        if self._mentions_password_field(combined_text) and any(keyword in combined_text for keyword in ("显示", "输入")):
            if self._is_error_message_expected(expected_text, verify_text):
                return []
            return ["    await expect(passwordInput).toHaveValue(runtimePassword || /.+/);"]

        # 标识符字段值
        if self._mentions_login_identifier(combined_text) and any(keyword in combined_text for keyword in ("显示", "输入")):
            if self._is_error_message_expected(expected_text, verify_text):
                return []
            value_expr = self._build_runtime_assert_expression("runtimeUsername", data_text)
            return [f"    await expect(identifierInput).toHaveValue({value_expr});"]

        # 按钮可见性
        if "按钮" in expected_text and ("可见" in expected_text or "点击" in expected_text or "enabled" in expected_text):
            return ["    await expect(submitButton).toBeVisible();"]

        return []

    def _generate_search_verify_lines(
        self,
        action_text: str,
        expected_text: str,
        verify_text: str,
        data_text: str,
        combined_text: str,
    ) -> List[str]:
        """生成搜索场景的验证代码"""
        # 空输入断言
        if self._is_blank_input_assertion(action_text, expected_text, verify_text):
            return ["    await expect(searchInput).toHaveValue('');"]

        lowered = " ".join([str(action_text or ""), str(expected_text or ""), str(verify_text or "")]).lower()

        if self._is_page_form_visibility_assertion(action_text, expected_text, verify_text):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(searchInput).toBeVisible();",
                "    await expect(searchButton).toBeVisible();",
            ]

        if (
            ("搜索框" in combined_text or "输入框" in combined_text or "search" in lowered)
            and ("显示" in combined_text or "输入" in combined_text or "value" in lowered)
        ):
            if data_text:
                return [f"    await expect(searchInput).toHaveValue({self._to_ts_string(data_text)});"]
            return ["    await expect(searchInput).toHaveValue(/.+/);"]

        if (
            "观察页面行为" in action_text
            or "observe" in lowered
            or "不跳转" in combined_text
            or "提示信息" in combined_text
        ):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(searchInput).toBeVisible();",
                "    await expect(searchButton).toBeVisible();",
            ]

        lowered = " ".join([str(action_text or ""), str(expected_text or ""), str(verify_text or "")]).lower()

        if (
            ("搜索框" in combined_text or "输入框" in combined_text or "search" in lowered)
            and ("显示" in combined_text or "输入" in combined_text or "value" in lowered)
        ):
            if data_text:
                return [f"    await expect(searchInput).toHaveValue({self._to_ts_string(data_text)});"]
            return ["    await expect(searchInput).toHaveValue(/.+/);"]

        if (
            "观察页面行为" in action_text
            or "observe" in lowered
            or "不跳转" in combined_text
            or "提示信息" in combined_text
        ):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(searchInput).toBeVisible();",
                "    await expect(searchButton).toBeVisible();",
            ]

        # 表单可见性断言
        if self._is_page_form_visibility_assertion(action_text, expected_text, verify_text):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(searchInput).toBeVisible();",
                "    await expect(searchButton).toBeVisible();",
            ]

        # 搜索结果页
        if "搜索结果页" in expected_text or "结果页面" in expected_text or "搜索结果" in expected_text or "结果列表" in expected_text:
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await expect.poll(() => page.url()).toMatch(/(wd|word|\\/s\\?)/);",
                "    await expect(page.locator('body')).toBeVisible();",
            ]

        # 搜索框可见性
        if ("搜索框" in expected_text or "输入框" in expected_text) and "可见" in expected_text:
            return ["    await expect(searchInput).toBeVisible();"]

        if ("定位" in expected_text or "存在" in expected_text) and ("搜索框" in expected_text or "输入框" in expected_text):
            return ["    await expect(searchInput).toBeVisible();"]

        # 搜索框值
        if ("输入框" in expected_text or "搜索框" in expected_text) and ("无任何字符" in expected_text or "为空" in expected_text):
            return ["    await expect(searchInput).toHaveValue('');"]

        if ("输入框" in expected_text or "搜索框" in expected_text) and ("显示" in expected_text or "输入" in expected_text):
            if data_text:
                return [f"    await expect(searchInput).toHaveValue({self._to_ts_string(data_text)});"]
            return ["    await expect(searchInput).toHaveValue(/.+/);"]

        # 按钮可见性
        if "按钮" in expected_text and ("可见" in expected_text or "点击" in expected_text or "enabled" in expected_text):
            return ["    await expect(searchButton).toBeVisible();"]

        return []

    def _generate_payment_verify_lines(
        self,
        action_text: str,
        expected_text: str,
        verify_text: str,
        data_text: str,
        combined_text: str,
    ) -> List[str]:
        """生成支付场景的验证代码"""
        # 金额输入框可见性
        if "金额" in combined_text and any(keyword in combined_text for keyword in ("可见", "存在", "显示")):
            return ["    await expect(amountInput).toBeVisible();"]

        # 按钮可见性
        if "按钮" in expected_text and ("可见" in expected_text or "点击" in expected_text):
            return ["    await expect(submitButton).toBeVisible();"]

        return []

    def _generate_form_verify_lines(
        self,
        action_text: str,
        expected_text: str,
        verify_text: str,
        data_text: str,
        combined_text: str,
    ) -> List[str]:
        """生成表单场景的验证代码"""
        # 表单可见性
        if self._is_page_form_visibility_assertion(action_text, expected_text, verify_text):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(formInput).toBeVisible();",
                "    await expect(submitButton).toBeVisible();",
            ]

        # 按钮可见性
        if "按钮" in expected_text and ("可见" in expected_text or "点击" in expected_text):
            return ["    await expect(submitButton).toBeVisible();"]

        return []

    def _generate_generic_verify_lines(
        self,
        action_text: str,
        expected_text: str,
        verify_text: str,
        data_text: str,
        combined_text: str,
    ) -> List[str]:
        """生成通用场景的验证代码

        对于通用场景，只在明确匹配时生成断言，否则返回空列表使用 ai() 验证
        """
        # 空输入断言
        if self._is_blank_input_assertion(action_text, expected_text, verify_text):
            if self._mentions_password_field(combined_text):
                return ["    await expect(passwordInput).toHaveValue('');"]
            if self._mentions_login_identifier(combined_text):
                return ["    await expect(identifierInput).toHaveValue('');"]
            return ["    await expect(searchInput).toHaveValue('');"]

        # 表单可见性断言
        if self._is_page_form_visibility_assertion(action_text, expected_text, verify_text):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(searchInput).toBeVisible();",
                "    await expect(searchButton).toBeVisible();",
            ]

        # 搜索结果页
        if "搜索结果页" in expected_text or "结果页面" in expected_text or "搜索结果" in expected_text or "结果列表" in expected_text:
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await expect.poll(() => page.url()).toMatch(/(wd|word|\\/s\\?)/);",
                "    await expect(page.locator('body')).toBeVisible();",
            ]

        # 对于其他情况，返回空列表，让调用方使用 ai() 语义验证
        return []

    def _contains_login_keywords(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return any(
            keyword in normalized
            for keyword in (
                "\u767b\u5f55",
                "\u8d26\u53f7",
                "\u8d26\u6237",
                "\u7528\u6237\u540d",
                "\u7528\u6237\u6807\u8bc6",
                "identifier",
                "username",
                "account",
                "email",
                "mobile",
                "phone",
            )
        )

    def _mentions_login_identifier(self, text: str) -> bool:
        normalized = str(text or "").lower()
        has_identifier = any(
            keyword in normalized
            for keyword in (
                "\u8d26\u53f7",
                "\u8d26\u6237",
                "\u7528\u6237\u540d",
                "\u7528\u6237\u6807\u8bc6",
                "identifier",
                "username",
                "account",
                "email",
                "mobile",
                "phone",
            )
        )
        return has_identifier and "\u5bc6\u7801" not in normalized and "password" not in normalized

    def _mentions_password_field(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return "\u5bc6\u7801" in normalized or "password" in normalized or "secret" in normalized

    def _is_login_submit_action(self, text: str) -> bool:
        normalized = str(text or "").lower()
        return ("\u70b9\u51fb" in normalized or "submit" in normalized or "click" in normalized) and any(
            keyword in normalized for keyword in ("\u767b\u5f55", "sign in", "signin", "submit")
        )

    def _is_empty_input_action(self, text: str) -> bool:
        normalized = str(text or "")
        return (
            ("\u4fdd\u6301" in normalized and "\u7a7a" in normalized and (
                "\u641c\u7d22\u6846" in normalized or "\u8f93\u5165\u6846" in normalized or self._contains_login_keywords(normalized) or self._mentions_password_field(normalized)
            ))
            or ("\u6e05\u7a7a" in normalized and (
                "\u641c\u7d22\u6846" in normalized or "\u8f93\u5165\u6846" in normalized or self._contains_login_keywords(normalized) or self._mentions_password_field(normalized)
            ))
        )

    def _is_negative_login_test(self, tc_type: str, tc_title: str, steps: List[Dict]) -> bool:
        """Detect if this is a negative login test that should NOT use runtime credentials.

        Negative tests include:
        - Tests with type "negative"
        - Tests with title containing "无效", "错误", "不存在", "失败"
        - Tests with steps mentioning wrong/invalid credentials
        """
        # Check test type
        if tc_type == "negative":
            return True

        # Check title for negative keywords
        title_lower = str(tc_title or "").lower()
        negative_title_keywords = (
            "无效", "错误", "不存在", "失败", "invalid", "wrong", "incorrect",
            "nonexistent", "failure", "失败", "异常"
        )
        if any(kw in title_lower for kw in negative_title_keywords):
            return True

        # Check steps for negative credential actions
        for step in steps:
            action = str(step.get("action", "") or "").lower()
            # Check if step mentions wrong/invalid password
            if self._mentions_password_field(action):
                if any(kw in action for kw in ("无效", "错误", "wrong", "invalid", "incorrect", "任意", "错误密码")):
                    return True

        return False

    def _is_error_message_expected(self, expected_text: str, verify_text: str) -> bool:
        """Detect if the test expects an error/failure message to appear.

        When error messages are expected, we should skip assertions on input fields
        because the page may have navigated away (login succeeded unexpectedly) or
        the input fields may no longer be visible.

        Returns True if the test is checking for error/failure scenarios.
        """
        combined = " ".join([str(expected_text or ""), str(verify_text or "")]).lower()

        error_keywords = (
            "错误提示", "错误信息", "登录失败", "用户不存在", "密码错误",
            "用户名或密码错误", "验证失败", "认证失败", "账号或密码错误",
            "invalid", "incorrect", "wrong", "error", "failure", "failed",
            "不存在", "提示信息", "失败", "异常"
        )

        # Check if this is specifically checking for error/failure messages
        is_checking_error = any(kw in combined for kw in error_keywords)

        # But exclude cases where we're checking that NO error occurred
        no_error_patterns = ("无错误", "无异常", "无报错", "no error", "成功", "正常")
        is_checking_no_error = any(kw in combined for kw in no_error_patterns)

        return is_checking_error and not is_checking_no_error

    def _build_runtime_fill_expression(self, runtime_var: str, fallback_value: str, fallback_literal: str = "test") -> str:
        if fallback_value:
            return f"{runtime_var} || {self._to_ts_string(fallback_value)}"
        return f"{runtime_var} || {self._to_ts_string(fallback_literal)}"

    def _build_runtime_assert_expression(self, runtime_var: str, fallback_value: str) -> str:
        if fallback_value:
            return f"{runtime_var} || {self._to_ts_string(fallback_value)}"
        return f"{runtime_var} || /.+/"

    def _generate_verify_lines(self, verify_prompt: str, label: str | None = None, scenario_type: ScenarioType = ScenarioType.GENERIC) -> List[str]:
        verify_text = label or verify_prompt
        lines = [f"    console.log({self._to_ts_string('[VERIFY] ' + verify_text)});"]
        native_lines = self._generate_native_verify_lines("", "", verify_text, verify_prompt, scenario_type)
        if native_lines:
            lines.extend(native_lines)
        else:
            lines.append(f"    await ai({self._to_ts_string('验证: ' + verify_prompt)});")
        return lines

    def _generate_native_url_assertions(self, verify_prompt: str) -> List[str]:
        lines = ["    await expect.poll(() => page.url()).not.toBe(initialUrl);"]
        if "搜索参数" in verify_prompt:
            lines.append("    await expect.poll(() => page.url()).toMatch(/(wd|word)=/);")
        return lines

    def _is_url_assertion(self, verify_prompt: str) -> bool:
        text = str(verify_prompt or "")
        return "URL" in text or "地址栏" in text

    def _is_blank_input_assertion(self, action: str, expected_text: str, verify_text: str) -> bool:
        combined = " ".join([str(action or ""), str(expected_text or ""), str(verify_text or "")])
        return (
            ("输入框" in combined or "搜索框" in combined)
            and any(keyword in combined for keyword in ("空白", "为空", "保持空"))
        )

    def _is_page_form_visibility_assertion(self, action: str, expected_text: str, verify_text: str) -> bool:
        combined = " ".join([str(action or ""), str(expected_text or ""), str(verify_text or "")])
        mentions_form = ("输入框" in combined or "搜索框" in combined) and "按钮" in combined
        mentions_visible_page = "页面" in combined and any(
            keyword in combined for keyword in ("加载", "显示", "可见", "包含")
        )
        return mentions_form and mentions_visible_page

    def _is_same_page_assertion(self, action: str, expected_text: str, verify_text: str) -> bool:
        combined = " ".join([str(action or ""), str(expected_text or ""), str(verify_text or "")])
        if any(keyword in combined for keyword in ("未跳转", "仍停留", "停留在登录页", "URL未变化")):
            return True
        return "不跳转" in combined and any(
            keyword in combined for keyword in ("登录", "主界面", "当前URL")
        )

    def _normalize_action_prompt(self, action: str, data: str, expected: str, action_prompt: str) -> str:
        prompt = self._sanitize_prompt(action_prompt)
        if self._is_placeholder_prompt(prompt) or "等待页面跳转或提示信息" in prompt:
            return self._convert_action_fallback(action, data, expected)
        return prompt

    def _normalize_verify_prompt(self, expected: str, verify_prompt: str) -> str:
        prompt = self._sanitize_prompt(verify_prompt)
        if self._is_placeholder_prompt(prompt):
            return self._convert_expected_fallback(expected)
        return prompt

    def _sanitize_prompt(self, prompt: str) -> str:
        value = str(prompt or "").strip()
        if value in {"", "N/A", "无", "null", "None", "待补充"}:
            return ""
        return value

    def _is_placeholder_prompt(self, prompt: str) -> bool:
        """Check if the prompt is a placeholder that should be replaced.

        A placeholder is an empty, vague, or non-actionable prompt that
        Midscene cannot execute. These should be replaced with native operations.
        """
        value = self._sanitize_prompt(prompt)
        # Empty prompts are placeholders
        if not value:
            return True
        # Vague prompts that Midscene cannot understand
        vague_prompts = {
            "等待页面稳定",
            "等待页面加载完成后继续",
            "继续下一步",
            "操作成功完成",
            "页面加载完成且状态稳定",
            "等待页面加载完成",
        }
        return value in vague_prompts

    def _convert_action_fallback(self, action: str, data: str, expected: str = "") -> str:
        """Convert action to a specific, executable Midscene prompt.

        Key principle: Generate specific, actionable prompts that Midscene can understand
        and execute. Avoid vague prompts like "等待页面稳定" or "操作成功完成".
        """
        action = str(action or "").strip()
        data = "" if data is None else str(data).strip()
        expected = "" if expected is None else str(expected).strip()
        action_lower = action.lower()
        expected_lower = expected.lower()

        if ("observe" in action_lower or "观察" in action) and ("history" in expected_lower or "历史记录" in expected):
            return "观察搜索框下拉建议或历史记录区域"
        if (
            "url" in action_lower
            or "跳转" in action
            or "地址栏" in action
            or "验证页面" in action
        ) and any(keyword in expected_lower for keyword in ("url", "result", "search")):
            return "观察地址栏URL变化或结果区域"

        # Specific action conversions based on action type
        if "观察" in action and "历史记录" in expected:
            return "观察搜索框下拉建议或历史记录区域"
        if ("观察" in action or "验证" in action or "检查" in action) and "搜索结果" in expected:
            return "等待搜索结果区域加载完成"
        if ("观察" in action or "验证" in action or "检查" in action) and ("报错" in expected or "异常" in expected):
            return "检查页面是否有报错或异常提示"
        if ("跳转" in action or "URL" in action) and ("搜索" in expected or "结果" in expected or "URL" in expected):
            return "等待页面加载完成"
        if "搜索结果页" in action or "结果页面" in action or "结果页" in action:
            return "等待搜索结果页面加载完成"

        # Data-driven actions
        if data and data not in {"N/A", "", "无", "登录页面地址"}:
            if "输入" in action or "填写" in action:
                if "邮箱" in action or "用户名" in action or "账号" in action:
                    return f'在用户名输入框输入 "{data}"'
                if "密码" in action:
                    return f'在密码输入框输入内容'
                if "搜索" in action or "关键词" in action:
                    return f'在搜索框输入 "{data}"'
                return f'在输入框输入 "{data}"'
            if "点击" in action:
                return f"点击 {data}"

        # Action-specific conversions
        if "打开" in action or "访问" in action or "导航" in action:
            return "等待页面加载完成"
        if "定位" in action and ("搜索框" in action or "输入框" in action):
            return "找到页面上的输入框"
        if "点击" in action:
            if "登录" in action:
                return "点击登录按钮"
            if "忘记密码" in action:
                return "点击忘记密码链接"
            if "搜索" in action or "百度一下" in action:
                return "点击搜索按钮"
            if "提交" in action:
                return "点击提交按钮"
            return "点击页面上的按钮"
        if "输入" in action:
            if "邮箱" in action or "用户名" in action or "账号" in action:
                return "在用户名输入框输入内容"
            if "密码" in action:
                return "在密码输入框输入内容"
            if "搜索" in action or "关键词" in action:
                return "在搜索框输入内容"
            return "在输入框输入内容"
        if "清空" in action and ("搜索框" in action or "输入框" in action):
            return "清空输入框内容"
        if "保持" in action and "空" in action:
            return "不执行任何输入操作"
        if "检查" in action or "验证" in action or "确认" in action:
            if "URL" in expected or "跳转" in expected:
                return "等待页面加载完成"
            if "搜索结果" in expected or "结果列表" in expected:
                return "等待搜索结果区域加载完成"
            # For generic check/verify actions, return empty to trigger native assertions
            return ""
        if "刷新" in action:
            return "刷新当前页面"
        if "等待" in action:
            return "等待页面加载完成"

        # For unhandled actions, return empty to let native handling take over
        return ""

    def _convert_expected_fallback(self, expected: str) -> str:
        """Convert expected result to a specific, verifiable Midscene prompt.

        Key principle: Generate specific, verifiable prompts that describe
        concrete page states. Avoid vague prompts like "操作成功完成".
        """
        expected = str(expected or "").strip()
        if not expected or expected == "N/A":
            return ""

        expected_lower = expected.lower()

        if (
            "stay on the current url" in expected_lower
            or "does not navigate away" in expected_lower
            or "remain on the current url" in expected_lower
        ):
            return "页面仍停留在当前URL"
        if (
            "remains empty" in expected_lower
            or "stays blank" in expected_lower
            or "remains blank" in expected_lower
        ):
            return "输入框保持空白状态"

        # Specific expected result conversions
        if (
            "仍停留在登录页面" in expected
            or "未跳转到主界面" in expected
            or "未跳转" in expected
            or "stay on current url" in expected_lower
        ):
            return "页面仍停留在当前URL"
        if ("搜索框" in expected or "搜索输入框" in expected or "search box" in expected_lower) and "可见" in expected:
            return "搜索框元素可见"
        if ("定位" in expected or "存在" in expected or "locate" in expected_lower) and (
            "搜索输入框" in expected or "搜索框" in expected or "search input" in expected_lower
        ):
            return "页面中存在搜索输入框"
        if "历史记录" in expected or "history" in expected_lower:
            return "页面显示搜索建议或历史记录"
        if "无报错" in expected or "no error" in expected_lower:
            return "页面没有错误提示"
        if "保持空白" in expected or "blank state" in expected_lower:
            return "输入框保持空白状态"
        if self._is_same_page_assertion("", expected, expected):
            return "页面停留在当前URL"
        if self._is_blank_input_assertion("", expected, expected):
            return "输入框内容为空"
        if self._is_page_form_visibility_assertion("", expected, expected):
            return "页面显示输入框和按钮"

        # Page load success - check before generic "成功" match
        if "页面" in expected and ("加载" in expected or "渲染" in expected or "显示" in expected):
            return "页面加载完成"
        if "登录页面" in expected and "成功" in expected:
            return "登录页面加载完成"

        if ("搜索框" in expected or "输入框" in expected) and "可见" in expected:
            return "输入框可见"
        if ("定位" in expected or "存在" in expected) and ("搜索框" in expected or "输入框" in expected):
            return "页面存在输入框"
        if ("输入框" in expected or "搜索框" in expected) and ("显示" in expected or "输入" in expected):
            return "输入框显示输入内容"
        if "清空" in expected or "cleared" in expected.lower():
            return "输入框内容为空"
        if "无报错" in expected or "无异常" in expected:
            return "页面没有错误提示"
        if "历史记录" in expected:
            return "页面显示搜索建议或历史记录"
        if "默认搜索页" in expected:
            return "页面保持在搜索页面"
        if "搜索结果页" in expected or "结果页面" in expected or "搜索结果" in expected or "结果列表" in expected or "结果" in expected:
            return "页面显示搜索结果"
        if "跳转" in expected or "URL" in expected:
            return "页面URL发生变化"
        if "错误" in expected or "提示" in expected or "信息" in expected:
            return "页面显示提示信息"
        if "按钮" in expected and ("可见" in expected or "点击" in expected or "enabled" in expected):
            return "按钮可见"
        if "可交互" in expected or "可点击" in expected:
            return "元素可交互"

        # For unhandled expected results, return empty to trigger native assertions
        return ""

    def _to_ts_string(self, value: str) -> str:
        return json.dumps(str(value), ensure_ascii=False)


if __name__ == "__main__":
    sample_test_cases = [
        {
            "id": "TC_001",
            "title": "用户正常登录",
            "priority": "high",
            "steps": [
                {"action": "输入用户名", "data": "admin"},
                {"action": "输入密码", "data": "password123"},
                {"action": "点击登录按钮", "data": ""},
            ],
            "expected": "登录成功",
            "tags": ["smoke"],
        }
    ]

    generator = MidsceneScriptGenerator(use_llm=False)
    path = generator.generate(sample_test_cases, "https://example.com/login")
    print(f"生成测试脚本: {path}")
