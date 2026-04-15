"""
测试 MidsceneScriptGenerator
"""
import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.automation.midscene_generator import MidsceneScriptGenerator
from core.utils.project_paths import GENERATED_TESTS_DIR


def test_generator_with_sample():
    """使用示例测试用例测试生成器"""
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
            "expected": "登录成功，显示欢迎信息",
            "tags": ["smoke"]
        }
    ]

    generator = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR))
    filepath = generator.generate(sample_test_cases, "https://example.com/login")

    print(f"生成测试脚本: {filepath}")

    # 读取并打印生成的内容
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'test("TC_001: 用户正常登录"' in content
    assert 'await ai("在邮箱或用户名输入框中输入 \\"admin\\"");' in content
    assert 'await page.goto("https://example.com/login");' in content

    print("\n" + "="*60)
    print("生成的脚本内容:")
    print("="*60)
    print(content)

    return filepath


def test_generator_with_real_data():
    """使用真实测试用例数据测试生成器"""
    # 查找最新的测试用例文件
    output_dir = "output"
    json_files = [f for f in os.listdir(output_dir) if f.startswith("test_cases") and f.endswith(".json")]

    if not json_files:
        print("未找到测试用例文件")
        return None

    # 使用最新的文件
    json_files.sort(reverse=True)
    json_path = os.path.join(output_dir, json_files[0])

    print(f"使用测试用例文件: {json_path}")

    generator = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR))
    filepath = generator.generate_from_json_file(json_path, "https://example.com/login")

    print(f"生成测试脚本: {filepath}")

    # 读取并打印前100行
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print("\n" + "="*60)
    print("生成的脚本内容 (前100行):")
    print("="*60)
    for line in lines[:100]:
        print(line, end='')

    return filepath


if __name__ == "__main__":
    print("="*60)
    print("测试 1: 使用示例数据")
    print("="*60)
    test_generator_with_sample()

    print("\n\n")
    print("="*60)
    print("测试 2: 使用真实数据")
    print("="*60)
    test_generator_with_real_data()
