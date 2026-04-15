"""
Midscene 测试脚本生成器

将测试用例（JSON格式）转换为 Midscene + Playwright 测试脚本（TypeScript）
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

from core.utils.project_paths import GENERATED_TESTS_DIR


class MidsceneScriptGenerator:
    """生成 Midscene + Playwright 测试脚本"""

    def __init__(self, output_dir: str = str(GENERATED_TESTS_DIR)):
        """
        初始化生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, test_cases: List[Dict], page_url: str = "https://example.com") -> str:
        """
        生成测试脚本文件

        Args:
            test_cases: 测试用例列表
            page_url: 目标页面URL

        Returns:
            生成的脚本文件路径
        """
        script_content = self._generate_script_content(test_cases, page_url)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auto_generated_{timestamp}.spec.ts"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(script_content)

        return filepath

    def generate_from_json_file(self, json_path: str, page_url: str = "https://example.com") -> str:
        """
        从JSON文件生成测试脚本

        Args:
            json_path: 测试用例JSON文件路径
            page_url: 目标页面URL

        Returns:
            生成的脚本文件路径
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        test_cases = data.get("test_cases", [])
        return self.generate(test_cases, page_url)

    def _generate_script_content(self, test_cases: List[Dict], page_url: str) -> str:
        """生成完整的脚本内容"""
        parts = [
            self._generate_header(),
            self._generate_imports(),
            self._generate_test_fixture(),
            "",
            self._generate_test_describe(test_cases, page_url)
        ]
        return "\n".join(parts)

    def _generate_header(self) -> str:
        """生成文件头部注释"""
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
        """生成导入语句"""
        return """import { test as base, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
import allure from 'allure-playwright';"""

    def _generate_test_fixture(self) -> str:
        """生成测试 fixture 扩展"""
        return """
// 扩展 test 以使用 Midscene AI fixture
const test = base.extend<{
  ai: any;
  aiAction: any;
  aiTap: any;
  aiInput: any;
  aiAssert: any;
  aiQuery: any;
}>(PlaywrightAiFixture());"""

    def _generate_test_describe(self, test_cases: List[Dict], page_url: str) -> str:
        """生成测试套件"""
        test_functions = []

        for tc in test_cases:
            test_func = self._generate_test_function(tc, page_url)
            test_functions.append(test_func)

        tests_content = "\n\n".join(test_functions)

        return f"""test.describe('自动生成的测试用例', () => {{
{tests_content}
}});"""

    def _generate_test_function(self, test_case: Dict, page_url: str) -> str:
        """生成单个测试函数"""
        tc_id = test_case.get("id", "TC_XXX")
        title = test_case.get("title", "未命名测试")
        steps = test_case.get("steps", [])
        expected = test_case.get("expected", "")
        tags = test_case.get("tags", [])
        priority = test_case.get("priority", "medium")

        test_name_literal = self._to_ts_string(f"{tc_id}: {title}")

        # 生成测试步骤
        test_steps = self._generate_test_steps(steps, page_url, expected)

        # 生成标签注释
        tag_comment = f"标签: {', '.join(tags)}" if tags else ""

        return f"""  test({test_name_literal}, async ({{ page, ai }}) => {{
    // 优先级: {priority}
    // {tag_comment}
{test_steps}
  }});"""

    def _generate_decorators(self, tc_id: str, title: str, priority: str, tags: List[str]) -> str:
        """生成测试装饰器"""
        lines = []

        # Allure 标题
        lines.append(f'@allure.title("{tc_id}: {title}")')

        # Allure 严重级别
        severity_map = {
            "critical": "BLOCKER",
            "high": "CRITICAL",
            "medium": "NORMAL",
            "low": "MINOR"
        }
        severity = severity_map.get(priority, "NORMAL")
        lines.append(f"@allure.severity(allure.severity_level.{severity})")

        # pytest 标签
        for tag in tags:
            lines.append(f"@pytest.mark.{tag}")

        return "\n    ".join(lines)

    def _generate_test_steps(self, steps: List[Dict], page_url: str, final_expected: str) -> str:
        """生成测试步骤代码"""
        lines = []
        lines.append("    // 访问目标页面")
        lines.append(f"    await page.goto({self._to_ts_string(page_url)});")
        lines.append("")

        for step in steps:
            step_lines = self._generate_single_step(step)
            lines.extend(step_lines)
            lines.append("")

        # 添加最终验证
        if final_expected:
            lines.append("    // 最终验证")
            ai_prompt = self._convert_expected_to_ai_prompt(final_expected)
            lines.append(f"    await ai({self._to_ts_string(f'验证: {ai_prompt}')});")

        return "\n".join(lines)

    def _generate_single_step(self, step: Dict) -> List[str]:
        """生成单个测试步骤"""
        lines = []

        if isinstance(step, str):
            step = {
                "action": step,
                "data": "",
                "expected": "",
            }

        action = step.get("action", "")
        data = step.get("data", "")
        expected = step.get("expected", "")

        # 生成步骤注释
        lines.append(f"    // 步骤: {action}")

        # 将 action 转换为 Midscene AI 指令
        ai_prompt = self._convert_action_to_ai_prompt(action, data)
        lines.append(f"    await ai({self._to_ts_string(ai_prompt)});")

        # 如果有预期结果，添加验证
        if expected and expected != "N/A":
            verify_prompt = self._convert_expected_to_ai_prompt(expected)
            lines.append(f"    await ai({self._to_ts_string(f'验证: {verify_prompt}')});")

        return lines

    def _convert_action_to_ai_prompt(self, action: str, data: str) -> str:
        """
        将测试步骤的 action 转换为 Midscene AI 指令

        Args:
            action: 原始操作描述
            data: 测试数据

        Returns:
            Midscene AI 指令
        """
        # 处理带数据的输入操作
        if data and data not in ["N/A", "", "登录页面地址"]:
            # 输入操作
            if "输入" in action or "填写" in action:
                # 提取输入框描述
                if "邮箱" in action or "用户名" in action:
                    return f'在邮箱或用户名输入框中输入 "{data}"'
                elif "密码" in action:
                    return f'在密码输入框中输入 "{data}"'
                elif "搜索" in action or "关键词" in action:
                    return f'在搜索框中输入 "{data}"'
                else:
                    return f'在输入框中输入 "{data}"'

            # 点击操作
            if "点击" in action:
                return f"点击 {data}"

        # 处理不带数据的操作
        # 打开页面
        if "打开" in action or "访问" in action:
            return "等待页面加载完成"

        # 点击操作 - 更精确的描述
        if "点击" in action:
            if "登录" in action:
                return "点击登录按钮"
            elif "忘记密码" in action:
                return "点击忘记密码链接"
            elif "搜索" in action or "百度" in action:
                return "点击搜索按钮"
            else:
                return "点击按钮"

        # 输入操作（无数据）- 更精确的描述
        if "输入" in action:
            if "邮箱" in action or "用户名" in action:
                return "在邮箱或用户名输入框中输入测试内容"
            elif "密码" in action:
                return "在密码输入框中输入测试内容"
            elif "搜索" in action or "关键词" in action:
                return "在搜索框中输入测试内容"
            else:
                return "在输入框中输入测试内容"

        # 保持为空
        if "保持" in action and "空" in action:
            return "不进行任何输入操作"

        # 检查操作
        if "检查" in action or "验证" in action:
            return "等待页面稳定"

        # 刷新页面
        if "刷新" in action:
            return "刷新当前页面"

        # 按键操作
        if "Tab" in action or "Enter" in action:
            return "按下键盘按键"

        # 执行登录流程
        if "执行" in action and "登录" in action:
            return "执行登录操作"

        # 默认情况：简化描述
        return "等待页面稳定"

    def _convert_expected_to_ai_prompt(self, expected: str) -> str:
        """
        将预期结果转换为 Midscene AI 验证指令

        Args:
            expected: 原始预期结果描述

        Returns:
            Midscene AI 验证指令
        """
        # 清理预期结果描述
        expected = expected.strip()

        # 搜索相关验证
        if "搜索结果" in expected or "结果" in expected:
            return "页面上显示了搜索结果列表"

        # 跳转相关
        if "跳转" in expected:
            return "页面URL发生了变化"

        # 成功/失败
        if "成功" in expected:
            return "操作成功完成"
        elif "失败" in expected:
            return "页面显示了错误提示信息"

        # 错误/提示
        if "错误" in expected or "提示" in expected:
            return "页面上显示了提示信息"

        # 显示相关
        if "显示" in expected:
            if "结果" in expected:
                return "页面上显示了搜索结果"
            return "页面显示了相关内容"

        # 默认：等待页面稳定
        return "页面加载完成且稳定"

    def _to_ts_string(self, value: str) -> str:
        """将 Python 字符串安全转换为 TypeScript 字符串字面量。"""
        return json.dumps(str(value), ensure_ascii=False)


# 使用示例
if __name__ == "__main__":
    # 示例测试用例
    sample_test_cases = [
        {
            "id": "TC_001",
            "title": "用户正常登录",
            "priority": "high",
            "steps": [
                {"action": "输入用户名", "data": "admin"},
                {"action": "输入密码", "data": "password123"},
                {"action": "点击登录按钮", "data": "N/A"}
            ],
            "expected": "登录成功",
            "tags": ["smoke"]
        }
    ]

    generator = MidsceneScriptGenerator()
    filepath = generator.generate(sample_test_cases, "https://example.com/login")
    print(f"生成测试脚本: {filepath}")
