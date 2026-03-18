"""Playwright测试脚本生成器"""
from typing import Dict, List


class ScriptGenerator:
    """将测试用例转换为Playwright脚本"""
    
    def generate(self, test_case: Dict) -> str:
        """
        生成Playwright测试脚本
        
        Args:
            test_case: 测试用例字典
            
        Returns:
            Python测试脚本代码
        """
        script = self._generate_header(test_case)
        script += self._generate_test_function(test_case)
        
        return script
    
    def _generate_header(self, test_case: Dict) -> str:
        """生成脚本头部"""
        return f'''"""
测试用例: {test_case["title"]}
ID: {test_case["id"]}
优先级: {test_case["priority"]}
"""
import pytest
import allure
from playwright.async_api import Page, expect


'''
    
    def _generate_test_function(self, test_case: Dict) -> str:
        """生成测试函数"""
        func_name = f"test_{test_case['id'].lower()}"
        
        # 生成装饰器
        decorators = self._generate_decorators(test_case)
        
        # 生成函数体
        body = self._generate_function_body(test_case)
        
        return f'''{decorators}
async def {func_name}(page: Page):
    """
    {test_case["title"]}
    """
{body}
'''
    
    def _generate_decorators(self, test_case: Dict) -> str:
        """生成Allure装饰器"""
        decorators = []
        
        decorators.append(f'@allure.title("{test_case["title"]}")')
        
        severity_map = {
            "critical": "CRITICAL",
            "high": "CRITICAL",
            "medium": "NORMAL",
            "low": "MINOR"
        }
        severity = severity_map.get(test_case.get("priority", "medium"), "NORMAL")
        decorators.append(f'@allure.severity(allure.severity_level.{severity})')
        
        if "tags" in test_case:
            for tag in test_case["tags"]:
                decorators.append(f'@pytest.mark.{tag}')
        
        return '\n'.join(decorators)
    
    def _generate_function_body(self, test_case: Dict) -> str:
        """生成函数体"""
        lines = []
        
        for i, step in enumerate(test_case.get("steps", []), 1):
            action = step.get("action", "")
            data = step.get("data", "")
            expected = step.get("expected", "")
            
            lines.append(f'    with allure.step("步骤{i}: {action}"):')
            
            # 根据action类型生成代码
            if "打开" in action or "访问" in action:
                url = data if data.startswith("http") else "https://example.com"
                lines.append(f'        await page.goto("{url}")')
            
            elif "输入" in action:
                # 简化处理：使用fill
                field_name = action.replace("输入", "").strip()
                lines.append(f'        # {action}')
                lines.append(f'        await page.fill("input", "{data}")')
            
            elif "点击" in action:
                button_text = action.replace("点击", "").replace("按钮", "").strip()
                lines.append(f'        # {action}')
                lines.append(f'        await page.click("button")')
            
            else:
                lines.append(f'        # TODO: {action}')
                lines.append(f'        pass')
            
            if expected:
                lines.append(f'        # 验证: {expected}')
                lines.append(f'        await page.wait_for_timeout(1000)')
            
            lines.append('')
        
        # 最终验证
        final_expected = test_case.get("expected", "")
        if final_expected:
            lines.append(f'    with allure.step("验证: {final_expected}"):')
            lines.append(f'        # TODO: 添加具体断言')
            lines.append(f'        pass')
        
        return '\n'.join(lines)
