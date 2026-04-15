"""主程序 - 阶段1演示"""
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from core.parsers.markdown_parser import parse_markdown
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.agents.test_case_generator import TestCaseGenerator
from core.automation.midscene_generator import MidsceneScriptGenerator
from core.utils.project_paths import (
    OUTPUT_DIR,
    GENERATED_TESTS_DIR,
    LEGACY_GENERATED_TESTS_DIR,
    ALLURE_RESULTS_DIR,
    ALLURE_REPORT_DIR,
    PLAYWRIGHT_RESULTS_DIR,
)


def get_timestamp() -> str:
    """获取当前时间戳，格式：(2026-04-03_12-30-45)"""
    return datetime.now().strftime("(%Y-%m-%d_%H-%M-%S)")


def clean_history_data():
    """
    清理历史数据

    在执行新任务前，清理 output 和生成脚本目录中的所有旧文件
    """
    output_dir = OUTPUT_DIR
    tests_dir = GENERATED_TESTS_DIR
    allure_results_dir = ALLURE_RESULTS_DIR
    allure_report_dir = ALLURE_REPORT_DIR
    test_results_dir = PLAYWRIGHT_RESULTS_DIR

    # 清理 output 目录
    if output_dir.exists():
        print("  [清理] output 目录...")
        for file in output_dir.iterdir():
            if file.is_file():
                file.unlink()
                print(f"    - 删除: {file.name}")

    # 清理新的生成脚本目录
    if tests_dir.exists():
        print(f"  [清理] {tests_dir} 目录...")
        for file in tests_dir.glob("*.spec.ts"):
            file.unlink()
            print(f"    - 删除: {file.name}")

    # 兼容清理旧目录，避免误读历史脚本
    if LEGACY_GENERATED_TESTS_DIR.exists():
        print("  [清理] tests/generated 旧目录...")
        for file in LEGACY_GENERATED_TESTS_DIR.glob("*.spec.ts"):
            file.unlink()
            print(f"    - 删除: {file.name}")

    # 清理历史执行产物，避免报告累计旧数据
    for directory in [allure_results_dir, allure_report_dir, test_results_dir]:
        if directory.exists():
            print(f"  [清理] {directory} 目录...")
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    import shutil
                    shutil.rmtree(item)
                print(f"    - 删除: {item.name}")


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
        output_dir = OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

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

    # 4. 生成测试脚本 (使用 Midscene)
    print("\n[步骤4] 生成测试脚本...")
    script_gen = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR))

    # 使用 Midscene 生成 TypeScript 测试脚本
    script_file = script_gen.generate(all_test_cases, page_url="https://example.com/login")
    print(f"  [OK] 生成测试脚本: {script_file}")

    print("[OK] 测试脚本生成完成")

    # 5. 提示下一步
    print("\n" + "=" * 60)
    print("[OK] 阶段1流程完成！")
    print("=" * 60)
    print(f"\n生成时间: {timestamp}")
    print("\n下一步操作：")
    print(f"1. 查看生成的测试用例: {test_cases_file}")
    print(f"2. 查看生成的测试脚本: {script_file}")
    print(f"3. 运行测试: npx playwright test {GENERATED_TESTS_DIR.as_posix()}/ --headed")
    print("\n注意: 使用 Midscene AI 进行元素定位，无需手动调整选择器")


if __name__ == "__main__":
    main()
