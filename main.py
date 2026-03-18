"""主程序 - 阶段1演示"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from parsers.markdown_parser import parse_markdown
from agents.requirement_analyzer import RequirementAnalyzer
from agents.test_case_generator import TestCaseGenerator
from automation.script_generator import ScriptGenerator


def main():
    """主流程"""
    # 加载环境变量
    load_dotenv()
    
    print("=" * 60)
    print("AI测试自动化平台 - 阶段1演示")
    print("=" * 60)
    
    # 1. 读取需求文档
    print("\n[步骤1] 读取需求文档...")
    requirement_file = "examples/requirement_login.md"
    
    if not os.path.exists(requirement_file):
        print(f"错误: 需求文档不存在 {requirement_file}")
        print("请先创建示例需求文档")
        return
    
    requirement_text = parse_markdown(requirement_file)
    print(f"✓ 需求文档读取成功 ({len(requirement_text)} 字符)")
    
    # 2. 分析需求
    print("\n[步骤2] 分析需求...")
    analyzer = RequirementAnalyzer()
    
    try:
        requirements = analyzer.analyze(requirement_text)
        print(f"✓ 需求分析完成，识别到 {len(requirements['requirements'])} 个需求")
        
        # 保存分析结果
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / "requirements.json", "w", encoding="utf-8") as f:
            json.dump(requirements, f, ensure_ascii=False, indent=2)
        print(f"  已保存到: output/requirements.json")
        
    except Exception as e:
        print(f"✗ 需求分析失败: {e}")
        return
    
    # 3. 生成测试用例
    print("\n[步骤3] 生成测试用例...")
    generator = TestCaseGenerator()
    
    all_test_cases = []
    for req in requirements["requirements"]:
        try:
            test_cases = generator.generate(req)
            all_test_cases.extend(test_cases)
            print(f"  ✓ {req['id']}: 生成 {len(test_cases)} 个测试用例")
        except Exception as e:
            print(f"  ✗ {req['id']}: 生成失败 - {e}")
    
    print(f"✓ 总共生成 {len(all_test_cases)} 个测试用例")
    
    # 保存测试用例
    with open(output_dir / "test_cases.json", "w", encoding="utf-8") as f:
        json.dump({"test_cases": all_test_cases}, f, ensure_ascii=False, indent=2)
    print(f"  已保存到: output/test_cases.json")
    
    # 4. 生成测试脚本
    print("\n[步骤4] 生成测试脚本...")
    script_gen = ScriptGenerator()
    
    tests_dir = Path("tests/generated")
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    for test_case in all_test_cases:
        script = script_gen.generate(test_case)
        script_file = tests_dir / f"{test_case['id'].lower()}.py"
        
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)
        
        print(f"  ✓ {test_case['id']}: {script_file}")
    
    print(f"✓ 测试脚本生成完成")
    
    # 5. 提示下一步
    print("\n" + "=" * 60)
    print("✓ 阶段1流程完成！")
    print("=" * 60)
    print("\n下一步操作：")
    print("1. 查看生成的测试用例: output/test_cases.json")
    print("2. 查看生成的测试脚本: tests/generated/")
    print("3. 运行测试: pytest tests/generated/ --alluredir=allure-results")
    print("4. 查看报告: allure serve allure-results")
    print("\n注意: 生成的脚本需要手动调整选择器才能实际运行")


if __name__ == "__main__":
    main()
