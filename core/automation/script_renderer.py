"""Render structured script plans into Midscene + Playwright test files."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable, List

from core.models.script_plan import (
    AssertionIntent,
    AssertionKind,
    ExecutionTarget,
    NativeOperation,
    NativeOperationKind,
    ScriptExecutionPlan,
    ScriptStepPlan,
)


class ScriptRenderer:
    """Render structured plans into executable TS scripts."""

    def render(self, plans: Iterable[ScriptExecutionPlan]) -> str:
        plan_list = list(plans)
        parts = [
            self._generate_header(),
            self._generate_imports(),
            self._generate_test_fixture(),
            "",
            self._generate_describe(plan_list),
        ]
        return "\n".join(parts)

    def _generate_header(self) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""/**
 * 自动生成的 Midscene 测试脚本
 *
 * 生成时间: {timestamp}
 * 生成器: ScriptRenderer
 *
 * 注意: 此文件由程序自动生成，请勿手动修改
 */"""

    def _generate_imports(self) -> str:
        return """import { test as base, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
import allure from 'allure-playwright';"""

    def _generate_test_fixture(self) -> str:
        return """
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
    console.log(`[SCREENSHOT] ${stepName} attached`);
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

    def _generate_describe(self, plans: List[ScriptExecutionPlan]) -> str:
        rendered_tests = [self._render_test(plan) for plan in plans]
        return "test.describe('自动生成的测试用例', () => {\n" + "\n\n".join(rendered_tests) + "\n});"

    def _render_test(self, plan: ScriptExecutionPlan) -> str:
        if plan.scenario.scenario_type == "login_only":
            return self._render_login_only_test(plan)

        body_lines = self._render_standard_body(plan)
        return f"""  test({self._to_ts_string(f"{plan.testcase_id}: {plan.title}")}, async ({{ page, ai }}, testInfo) => {{
    console.log({self._to_ts_string(f"[TEST-START] {plan.testcase_id}: {plan.title}")});
    try {{
{body_lines}
    }} finally {{
      await attachFinalScreenshot(page, testInfo);
    }}
    console.log({self._to_ts_string(f"[TEST-END] {plan.testcase_id}: {plan.title}")});
  }});"""

    def _render_standard_body(self, plan: ScriptExecutionPlan) -> str:
        lines: List[str] = [
            f"    // scenario_type: {plan.scenario.scenario_type}",
            f"    // execution_policy: {plan.scenario.execution_policy.value}",
            "    console.log('[STEP] Open target page');",
            f"    await page.goto({self._to_ts_string(plan.setup.page_url)});",
            f"    await page.waitForLoadState({self._to_ts_string(plan.setup.wait_for)});",
        ]
        if plan.setup.initial_wait_ms:
            lines.append(f"    await page.waitForTimeout({plan.setup.initial_wait_ms});")

        if self._needs_initial_url(plan):
            lines.append("    const initialUrl = page.url();")

        if plan.scenario.requires_runtime_credentials:
            username_env = plan.setup.required_env_vars[0] if len(plan.setup.required_env_vars) > 0 else "LOGIN_USERNAME"
            password_env = plan.setup.required_env_vars[1] if len(plan.setup.required_env_vars) > 1 else "LOGIN_PASSWORD"
            lines.extend(
                [
                    f"    const runtimeUsername = process.env[{self._to_ts_string(username_env)}] ?? '';",
                    f"    const runtimePassword = process.env[{self._to_ts_string(password_env)}] ?? '';",
                ]
            )

        lines.extend(self._render_locators(plan))
        lines.extend(["", "    await attachStepScreenshot(page, '01-initial-page', testInfo);", ""])

        for step_index, step in enumerate(plan.steps, start=2):
            step_name = self._safe_step_name(step_index, step.original_action)
            lines.append(f"    // Step: {step.original_action}")
            lines.append(f"    console.log({self._to_ts_string('[STEP] ' + step.original_action)});")
            lines.extend(self._render_step_action(step))
            lines.extend(self._render_step_assertions(step))
            lines.append(f"    await attachStepScreenshot(page, {self._to_ts_string(step_name)}, testInfo);")
            lines.append("")

        if plan.final_assertions:
            lines.append("    // Final verify")
            final_expected = str(plan.metadata.get("final_expected") or "final assertions")
            lines.append(f"    console.log({self._to_ts_string('[FINAL-VERIFY] ' + final_expected)});")
            lines.extend(self._render_assertions(plan.final_assertions, fallback_prompt=final_expected))
            lines.append("    await attachStepScreenshot(page, 'final-verify', testInfo);")

        return "\n".join(lines)

    def _render_login_only_test(self, plan: ScriptExecutionPlan) -> str:
        success_value = str(plan.metadata.get("success_signal_value") or "LianLian")
        success_type = str(plan.metadata.get("success_signal_type") or "visual_text_or_logo")
        manual_wait_timeout_ms = int(plan.metadata.get("manual_wait_timeout_ms") or 180000)
        username_env = str(plan.metadata.get("username_env") or "LOGIN_USERNAME")
        password_env = str(plan.metadata.get("password_env") or "LOGIN_PASSWORD")
        forbidden_actions = ", ".join(plan.metadata.get("forbidden_actions") or []) or "none"
        success_logo_selector = self._build_success_logo_selector(success_value, success_type)
        identifier_selector = plan.scenario.selectors.get("identifierInput", "input:visible")
        password_selector = plan.scenario.selectors.get("passwordInput", 'input[type="password"]:visible')
        submit_selector = plan.scenario.selectors.get("submitButton", "button:visible")

        body = "\n".join(
            [
                f"    const loginUsername = process.env[{self._to_ts_string(username_env)}];",
                f"    const loginPassword = process.env[{self._to_ts_string(password_env)}];",
                "    if (!loginUsername || !loginPassword) {",
                f"      throw new Error('Missing login credentials. Add identifier/password to the requirement file, or configure {username_env}/{password_env} in .env.');",
                "    }",
                f"    const identifierInput = page.locator({self._to_ts_string(identifier_selector)}).first();",
                f"    const passwordInput = page.locator({self._to_ts_string(password_selector)}).first();",
                f"    const submitButton = page.locator({self._to_ts_string(submit_selector)}).first();",
                f"    const successText = page.getByText({self._to_ts_string(success_value)}, {{ exact: false }});",
                f"    const successLogo = page.locator({self._to_ts_string(success_logo_selector)}).first();",
                "    const successSignal = successLogo.or(successText).first();",
                "    let maskedFields = [];",
                "    maskedFields = [identifierInput, passwordInput];",
                "    console.log('[STEP] Open login page');",
                f"    await page.goto({self._to_ts_string(plan.setup.page_url)});",
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
        return f"""  test({self._to_ts_string(f"{plan.testcase_id}: {plan.title}")}, async ({{ page, ai }}, testInfo) => {{
    // scenario_type: login_only
    // forbidden_actions: {forbidden_actions}
    console.log({self._to_ts_string(f"[TEST-START] {plan.testcase_id}: {plan.title}")});
    let maskedFields = [];
    try {{
{body}
    }} finally {{
      await attachFinalScreenshot(page, testInfo, {{ mask: maskedFields }});
    }}
    console.log({self._to_ts_string(f"[TEST-END] {plan.testcase_id}: {plan.title}")});
  }});"""

    def _render_locators(self, plan: ScriptExecutionPlan) -> List[str]:
        lines: List[str] = []
        for alias, selector in plan.scenario.selectors.items():
            lines.append(f"    const {alias} = page.locator({self._to_ts_string(selector)}).first();")
        return lines

    def _render_step_action(self, step: ScriptStepPlan) -> List[str]:
        lines: List[str] = []
        use_ai = step.preferred_executor in {ExecutionTarget.MIDSCENE_AI, ExecutionTarget.MIXED}
        if step.native_operations:
            lines.extend(self._render_native_operations(step.native_operations))
        if use_ai and step.action_prompt and (step.preferred_executor == ExecutionTarget.MIDSCENE_AI or not step.native_operations):
            lines.append(f"    await ai({self._to_ts_string(step.action_prompt)});")
        return lines

    def _render_step_assertions(self, step: ScriptStepPlan) -> List[str]:
        if step.assertion_intents:
            return self._render_assertions(step.assertion_intents, fallback_prompt=step.verify_prompt)
        if step.verify_prompt:
            return [f"    await ai({self._to_ts_string('Verify: ' + step.verify_prompt)});"]
        return []

    def _render_native_operations(self, operations: List[NativeOperation]) -> List[str]:
        lines: List[str] = []
        for operation in operations:
            if operation.kind == NativeOperationKind.EXPECT_VISIBLE and operation.locator:
                lines.append(f"    await expect({operation.locator}).toBeVisible();")
            elif operation.kind == NativeOperationKind.FILL and operation.locator:
                value_expr = self._build_fill_expression(operation)
                lines.append(f"    await {operation.locator}.fill({value_expr});")
            elif operation.kind == NativeOperationKind.CLICK and operation.locator:
                lines.append(f"    await {operation.locator}.click();")
            elif operation.kind == NativeOperationKind.WAIT_LOAD:
                lines.append("    await page.waitForLoadState('domcontentloaded');")
            elif operation.kind == NativeOperationKind.WAIT_TIMEOUT:
                lines.append(f"    await page.waitForTimeout({operation.timeout_ms or 1000});")
        return lines

    def _render_assertions(self, assertions: List[AssertionIntent], fallback_prompt: str = "") -> List[str]:
        lines: List[str] = []
        for assertion in assertions:
            if assertion.kind == AssertionKind.PAGE_BODY_VISIBLE:
                lines.append("    await expect(page.locator('body')).toBeVisible();")
            elif assertion.kind == AssertionKind.LOCATOR_VISIBLE and assertion.locator:
                lines.append(f"    await expect({assertion.locator}).toBeVisible();")
            elif assertion.kind == AssertionKind.VALUE_EMPTY and assertion.locator:
                lines.append(f"    await expect({assertion.locator}).toHaveValue('');")
            elif assertion.kind == AssertionKind.VALUE_NONEMPTY and assertion.locator:
                lines.append(f"    await expect({assertion.locator}).toHaveValue(/.+/);")
            elif assertion.kind == AssertionKind.VALUE_EQUALS and assertion.locator:
                expr = self._build_assert_expression(assertion)
                lines.append(f"    await expect({assertion.locator}).toHaveValue({expr});")
            elif assertion.kind == AssertionKind.URL_SAME:
                lines.append("    await expect.poll(() => page.url()).toBe(initialUrl);")
            elif assertion.kind == AssertionKind.URL_CHANGED:
                lines.append("    await expect.poll(() => page.url()).not.toBe(initialUrl);")
            elif assertion.kind == AssertionKind.URL_MATCHES and assertion.regex:
                lines.append(f"    await expect.poll(() => page.url()).toMatch(/{assertion.regex}/);")
            elif assertion.kind == AssertionKind.TEXT_VISIBLE and assertion.expected_value:
                lines.append(
                    f"    await expect(page.getByText({self._to_ts_string(assertion.expected_value)}, {{ exact: {str(assertion.exact).lower()} }})).toBeVisible();"
                )

        if not lines and fallback_prompt:
            lines.append(f"    await ai({self._to_ts_string('Verify: ' + fallback_prompt)});")
        return lines

    def _needs_initial_url(self, plan: ScriptExecutionPlan) -> bool:
        all_assertions = list(plan.final_assertions)
        for step in plan.steps:
            all_assertions.extend(step.assertion_intents)
        return any(assertion.kind in {AssertionKind.URL_SAME, AssertionKind.URL_CHANGED, AssertionKind.URL_MATCHES} for assertion in all_assertions)

    def _build_fill_expression(self, operation: NativeOperation) -> str:
        if operation.value is not None:
            return self._to_ts_string(operation.value)
        if operation.runtime_var and operation.fallback_value is not None:
            return f"{operation.runtime_var} || {self._to_ts_string(operation.fallback_value)}"
        if operation.runtime_var:
            return f"{operation.runtime_var} || ''"
        return self._to_ts_string(operation.fallback_value or "")

    def _build_assert_expression(self, assertion: AssertionIntent) -> str:
        if assertion.runtime_var and assertion.expected_value:
            return f"{assertion.runtime_var} || {self._to_ts_string(assertion.expected_value)}"
        if assertion.runtime_var:
            return f"{assertion.runtime_var} || /.+/"
        return self._to_ts_string(assertion.expected_value or "")

    def _safe_step_name(self, step_index: int, action: str) -> str:
        snippet = (action or "step").replace("\n", " ").strip()[:15]
        return f"{step_index:02d}-{snippet}"

    def _build_success_logo_selector(self, success_value: str, success_type: str) -> str:
        escaped = success_value.replace("\\", "\\\\").replace('"', '\\"')
        if success_type == "visual_text_or_logo":
            return (
                f'img[alt*="{escaped}" i], '
                f'[aria-label*="{escaped}" i], '
                f'[title*="{escaped}" i], '
                f'img[src*="{escaped.lower()}" i]'
            )
        return f'[aria-label*="{escaped}" i], [title*="{escaped}" i]'

    def _to_ts_string(self, value: str) -> str:
        return json.dumps(str(value), ensure_ascii=False)
