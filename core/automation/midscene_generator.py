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
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.utils.llm_client import get_llm_client
from core.utils.project_paths import GENERATED_TESTS_DIR


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
        os.makedirs(output_dir, exist_ok=True)

    @property
    def llm_client(self):
        if self._llm_client is None and self.use_llm:
            self._llm_client = get_llm_client()
        return self._llm_client

    def generate(
        self,
        test_cases: List[Dict],
        page_url: str = "https://example.com",
        scenario_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        script_content = self._generate_script_content(
            test_cases,
            page_url,
            scenario_config=scenario_config,
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
    ) -> str:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.generate(
            data.get("test_cases", []),
            page_url,
            scenario_config=scenario_config,
        )

    def _generate_script_content(
        self,
        test_cases: List[Dict],
        page_url: str,
        scenario_config: Optional[Dict[str, Any]] = None,
    ) -> str:
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
            test_functions = [self._generate_test_function(tc, page_url) for tc in test_cases]
        return "test.describe('自动生成的测试用例', () => {\n" + "\n\n".join(test_functions) + "\n});"

    def _generate_test_function(self, test_case: Dict, page_url: str) -> str:
        tc_id = test_case.get("id", "TC_XXX")
        title = test_case.get("title", "未命名测试")
        steps = test_case.get("steps", [])
        expected = test_case.get("expected", "")
        tags = test_case.get("tags", [])
        priority = test_case.get("priority", "medium")

        tag_comment = f"标签: {', '.join(tags)}" if tags else ""
        body = self._generate_test_steps(steps, page_url, expected)
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
                f"      throw new Error('Missing {username_env} or {password_env} environment variables.');",
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

    def _generate_test_steps(self, steps: List[Dict], page_url: str, final_expected: str) -> str:
        lines = [
            "    // 访问目标页面",
            "    console.log('[STEP] 打开目标页面');",
            f"    await page.goto({self._to_ts_string(page_url)});",
            "    await page.waitForLoadState('domcontentloaded');",
            "    await page.waitForTimeout(1500);",
            "    const initialUrl = page.url();",
            "    const searchInput = page.locator('#kw:visible, input[name=\"wd\"]:visible, textarea[name=\"wd\"]:visible, input.s_ipt:visible, textarea.s_ipt:visible, input:visible, textarea:visible').first();",
            "    const searchButton = page.locator('#su:visible, input[type=\"submit\"]:visible, button:visible').first();",
            "",
        ]

        converted_steps = self._convert_steps_with_llm(steps) if self.use_llm and self.llm_client and steps else self._fallback_convert_steps(steps)

        for step in converted_steps:
            original_action = step.get("original_action", "")
            action_prompt = step.get("action_prompt", "")
            verify_prompt = step.get("verify_prompt", "")
            expected_text = step.get("expected_text", "")
            data = step.get("data", "")

            lines.append(f"    // 步骤: {original_action}")
            lines.append(f"    console.log({self._to_ts_string('[STEP] ' + original_action)});")

            native_action_lines = self._generate_native_action_lines(original_action, data, expected_text)
            if native_action_lines:
                lines.extend(native_action_lines)
            else:
                lines.append(f"    await ai({self._to_ts_string(action_prompt or self._convert_action_fallback(original_action, data, expected_text))});")

            if verify_prompt:
                lines.append(f"    console.log({self._to_ts_string('[VERIFY] ' + (expected_text or verify_prompt))});")
                native_verify_lines = self._generate_native_verify_lines(original_action, data, expected_text, verify_prompt)
                if native_verify_lines:
                    lines.extend(native_verify_lines)
                else:
                    lines.append(f"    await ai({self._to_ts_string('验证: ' + verify_prompt)});")

            lines.append("")

        final_verify = self._convert_expected_fallback(final_expected)
        if final_verify:
            lines.append("    // 最终验证")
            lines.append(f"    console.log({self._to_ts_string('[FINAL-VERIFY] ' + final_expected)});")
            native_final_lines = self._generate_native_verify_lines("最终验证", "", final_expected, final_verify)
            if native_final_lines:
                lines.extend(native_final_lines)
            else:
                lines.append(f"    await ai({self._to_ts_string('验证: ' + final_verify)});")

        return "\n".join(lines)

    def _convert_steps_with_llm(self, steps: List[Dict]) -> List[Dict]:
        steps_desc = []
        for i, step in enumerate(steps, 1):
            action = step.get("action", "") if isinstance(step, dict) else str(step)
            data = step.get("data", "") if isinstance(step, dict) else ""
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
                data = step.get("data", "") if isinstance(step, dict) else ""
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
            data = step.get("data", "") if isinstance(step, dict) else ""
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

    def _generate_native_action_lines(self, action: str, data: str, expected: str) -> List[str]:
        action_text = str(action or "")
        data_text = "" if data is None else str(data)

        if "定位" in action_text and ("搜索框" in action_text or "输入框" in action_text):
            return ["    await expect(searchInput).toBeVisible();"]

        if ("保持" in action_text and "空" in action_text and ("搜索框" in action_text or "输入框" in action_text)) or (
            "清空" in action_text and ("搜索框" in action_text or "输入框" in action_text)
        ):
            return ["    await searchInput.fill('');"]

        if ("输入" in action_text or "可输入" in action_text) and ("搜索框" in action_text or "输入框" in action_text):
            return [f"    await searchInput.fill({self._to_ts_string(data_text or 'test')});"]

        if "点击" in action_text and ("搜索" in action_text or "百度一下" in action_text):
            return [
                "    await expect(searchButton).toBeVisible();",
                "    await searchButton.click();",
            ]

        if "搜索结果页" in action_text or "结果页面" in action_text or "结果页" in action_text:
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await page.waitForTimeout(1500);",
            ]

        if "观察页面行为" in action_text and ("提示" in expected or "不跳转" in expected or "空" in expected):
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await page.waitForTimeout(1200);",
            ]

        return []

    def _generate_native_verify_lines(self, action: str, data: str, expected: str, verify_prompt: str) -> List[str]:
        expected_text = str(expected or "")
        verify_text = str(verify_prompt or "")
        data_text = "" if data is None else str(data)

        if self._is_url_assertion(verify_text):
            return self._generate_native_url_assertions(verify_text)

        if ("提示" in expected_text or "不跳转" in expected_text or "空输入" in expected_text) and (
            "页面行为" in action or "系统行为" in action or "空" in expected_text
        ):
            return [
                "    await expect(page.locator('body')).toBeVisible();",
                "    await expect(searchInput).toBeVisible();",
                "    await expect(searchButton).toBeVisible();",
            ]

        if "搜索结果页" in expected_text or "结果页面" in expected_text or "搜索结果" in expected_text or "结果列表" in expected_text:
            return [
                "    await page.waitForLoadState('domcontentloaded');",
                "    await expect.poll(() => page.url()).toMatch(/(wd|word|\\/s\\?)/);",
                "    await expect(page.locator('body')).toBeVisible();",
            ]

        if ("搜索框" in expected_text or "输入框" in expected_text) and "可见" in expected_text:
            return ["    await expect(searchInput).toBeVisible();"]

        if ("定位" in expected_text or "存在" in expected_text) and ("搜索框" in expected_text or "输入框" in expected_text):
            return ["    await expect(searchInput).toBeVisible();"]

        if ("输入框" in expected_text or "搜索框" in expected_text) and ("无任何字符" in expected_text or "为空" in expected_text):
            return ["    await expect(searchInput).toHaveValue('');"]

        if ("输入框" in expected_text or "搜索框" in expected_text) and ("显示" in expected_text or "输入" in expected_text):
            if data_text:
                return [f"    await expect(searchInput).toHaveValue({self._to_ts_string(data_text)});"]
            return ["    await expect(searchInput).toHaveValue(/.+/);"]

        if "按钮" in expected_text and ("可见" in expected_text or "点击" in expected_text or "enabled" in expected_text):
            return ["    await expect(searchButton).toBeVisible();"]

        return []

    def _generate_verify_lines(self, verify_prompt: str, label: str | None = None) -> List[str]:
        verify_text = label or verify_prompt
        lines = [f"    console.log({self._to_ts_string('[VERIFY] ' + verify_text)});"]
        native_lines = self._generate_native_verify_lines("", "", verify_text, verify_prompt)
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
        value = self._sanitize_prompt(prompt)
        return value in {"", "等待页面稳定", "等待页面加载完成后继续", "继续下一步"}

    def _convert_action_fallback(self, action: str, data: str, expected: str = "") -> str:
        action = str(action or "").strip()
        data = "" if data is None else str(data).strip()
        expected = "" if expected is None else str(expected).strip()

        if "观察" in action and "历史记录" in expected:
            return "观察搜索框下拉建议或历史记录区域，并确认页面没有报错提示"
        if ("观察" in action or "验证" in action or "检查" in action) and "搜索结果" in expected:
            return "等待搜索结果区域加载完成并观察结果列表"
        if ("观察" in action or "验证" in action or "检查" in action) and ("报错" in expected or "异常" in expected):
            return "观察页面是否出现报错、异常提示或空白崩溃"
        if ("跳转" in action or "URL" in action) and ("搜索" in expected or "结果" in expected or "URL" in expected):
            return "等待页面加载完成并观察地址栏和结果区域变化"
        if "搜索结果页" in action or "结果页面" in action or "结果页" in action:
            return "等待搜索结果页面加载完成"

        if data and data not in {"N/A", "", "无", "登录页面地址"}:
            if "输入" in action or "填写" in action:
                if "邮箱" in action or "用户名" in action:
                    return f'在邮箱或用户名输入框中输入 "{data}"'
                if "密码" in action:
                    return f'在密码输入框中输入 "{data}"'
                if "搜索" in action or "关键词" in action:
                    return f'在搜索框中输入 "{data}"'
                return f'在输入框中输入 "{data}"'
            if "点击" in action:
                return f"点击 {data}"

        if "打开" in action or "访问" in action:
            return "等待页面加载完成"
        if "定位" in action and ("搜索框" in action or "输入框" in action):
            return "观察并定位页面上的搜索输入框"
        if "点击" in action:
            if "登录" in action:
                return "点击登录按钮"
            if "忘记密码" in action:
                return "点击忘记密码链接"
            if "搜索" in action or "百度一下" in action:
                return "点击搜索按钮"
            return "点击按钮"
        if "输入" in action:
            if "邮箱" in action or "用户名" in action:
                return "在邮箱或用户名输入框中输入测试内容"
            if "密码" in action:
                return "在密码输入框中输入测试内容"
            if "搜索" in action or "关键词" in action:
                return "在搜索框中输入测试内容"
            return "在输入框中输入测试内容"
        if "清空" in action and ("搜索框" in action or "输入框" in action):
            return "清空搜索框内容"
        if "保持" in action and "空" in action:
            return "保持搜索框为空，不执行任何输入操作"
        if "检查" in action or "验证" in action:
            if "URL" in expected or "跳转" in expected:
                return "等待页面加载完成并观察地址栏变化"
            if "搜索结果" in expected or "结果列表" in expected:
                return "等待搜索结果区域加载完成并观察结果列表"
            return "等待页面稳定"
        if "刷新" in action:
            return "刷新当前页面"
        return "等待页面稳定"

    def _convert_expected_fallback(self, expected: str) -> str:
        expected = str(expected or "").strip()
        if not expected or expected == "N/A":
            return ""
        if ("搜索框" in expected or "输入框" in expected) and "可见" in expected:
            return "搜索框元素可见"
        if ("定位" in expected or "存在" in expected) and ("搜索框" in expected or "输入框" in expected):
            return "页面中存在搜索输入框"
        if ("输入框" in expected or "搜索框" in expected) and ("显示" in expected or "输入" in expected):
            return "输入框中显示了已输入文本"
        if "无报错" in expected or "无异常" in expected:
            return "页面未显示错误提示，且仍然可以正常交互"
        if "历史记录" in expected:
            return "页面显示了搜索建议或历史记录，且未出现错误提示"
        if "默认搜索页" in expected:
            return "页面保持在可正常交互的搜索页面，且未出现错误提示"
        if "搜索结果页" in expected or "结果页面" in expected or "搜索结果" in expected or "结果列表" in expected or "结果" in expected:
            return "页面显示了搜索结果列表"
        if "跳转" in expected or "URL" in expected:
            return "页面URL发生了变化"
        if "错误" in expected or "提示" in expected:
            return "页面显示了提示信息"
        if "按钮" in expected and ("可见" in expected or "点击" in expected or "enabled" in expected):
            return "搜索按钮可见且可交互"
        if "成功" in expected:
            return "操作成功完成"
        return "页面加载完成且状态稳定"

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
