"""主程序 - 阶段1演示"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from parsers.markdown_parser import parse_markdown
from agents.requirement_analyzer import RequirementAnalyzer
from agents.test_case_generator import TestCaseGenerator
from automation.script_generator import ScriptGenerator


def get_timestamp() -> str:
    """获取当前时间戳，格式：(2026-04-03_12-30-45)"""
    return datetime.now().strftime("(%Y-%m-%d_%H-%M-%S)")


def clean_history_data():
    """
    清理历史数据

    在执行新任务前，清理 output 和 tests/generated 目录中的所有旧文件
    """
    output_dir = Path("output")
    tests_dir = Path("tests/generated")

    # 清理 output 目录
    if output_dir.exists():
        print("  [清理] output 目录...")
        for file in output_dir.iterdir():
            if file.is_file():
                file.unlink()
                print(f"    - 删除: {file.name}")

    # 清理 tests/generated 目录
    if tests_dir.exists():
        print("  [清理] tests/generated 目录...")
        for file in tests_dir.glob("*.py"):
            file.unlink()
            print(f"    - 删除: {file.name}")


def main():
    """主流程"""
    # 加载环境变量
    load_dotenv()

    print("=" * 60)
    print("AI测试自动化平台 - 阶段1演示")
    print("=" * 60)

    # 0. 清理历史数据
    print("\n[步骤0] 清理历史数据...")
    clean_history_data()

    # 获取时间戳
    timestamp = get_timestamp()

    # 1. 读取需求文档
    print("\n[步骤1] 读取需求文档...")
    requirement_file = "examples/requirement_login.md"

    if not os.path.exists(requirement_file):
        print(f"错误: 需求文档不存在 {requirement_file}")
        print("请先创建示例需求文档")
        return

    requirement_text = parse_markdown(requirement_file)
    print(f"[OK] 需求文档读取成功 ({len(requirement_text)} 字符)")

    # 2. 分析需求
    print("\n[步骤2] 分析需求...")
    analyzer = RequirementAnalyzer()

    try:
        requirements = analyzer.analyze(requirement_text)
        print(f"[OK] 需求分析完成，识别到 {len(requirements['requirements'])} 个需求")

        # 保存分析结果
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        requirements_file = output_dir / f"requirements{timestamp}.json"
        with open(requirements_file, "w", encoding="utf-8") as f:
            json.dump(requirements, f, ensure_ascii=False, indent=2)
        print(f"  已保存到: {requirements_file}")

    except Exception as e:
        print(f"[FAIL] 需求分析失败: {e}")
        return

    # 3. 生成测试用例
    print("\n[步骤3] 生成测试用例...")
    generator = TestCaseGenerator()

    all_test_cases = []
    for req in requirements["requirements"]:
        try:
            test_cases = generator.generate(req)
            all_test_cases.extend(test_cases)
            print(f"  [OK] {req['id']}: 生成 {len(test_cases)} 个测试用例")
        except Exception as e:
            print(f"  [FAIL] {req['id']}: 生成失败 - {e}")

    print(f"[OK] 总共生成 {len(all_test_cases)} 个测试用例")

    # 保存测试用例
    test_cases_file = output_dir / f"test_cases{timestamp}.json"
    with open(test_cases_file, "w", encoding="utf-8") as f:
        json.dump({"test_cases": all_test_cases}, f, ensure_ascii=False, indent=2)
    print(f"  已保存到: {test_cases_file}")

    # 4. 生成测试脚本
    print("\n[步骤4] 生成测试脚本...")
    script_gen = ScriptGenerator()

    tests_dir = Path("tests/generated")
    tests_dir.mkdir(parents=True, exist_ok=True)

    for test_case in all_test_cases:
        script = script_gen.generate(test_case)
        script_file = tests_dir / f"{test_case['id'].lower()}{timestamp}.py"

        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        print(f"  [OK] {test_case['id']}: {script_file}")

    print(f"[OK] 测试脚本生成完成")

    # 5. 提示下一步
    print("\n" + "=" * 60)
    print("[OK] 阶段1流程完成！")
    print("=" * 60)
    print(f"\n生成时间: {timestamp}")
    print("\n下一步操作：")
    print(f"1. 查看生成的测试用例: {test_cases_file}")
    print(f"2. 查看生成的测试脚本: tests/generated/*{timestamp}.py")
    print("3. 运行测试: pytest tests/generated/ --alluredir=allure-results")
    print("4. 查看报告: allure serve allure-results")
    print("\n注意: 生成的脚本需要手动调整选择器才能实际运行")


if __name__ == "__main__":
    main()
