"""
主程序 - 阶段3：完整自动化测试流程

使用 LangGraph 实现 Agent 协作：
- 需求分析 Agent
- 测试用例生成 Agent
- 测试用例评审 Agent
- 脚本生成（Midscene）
- 测试执行
- 反馈循环
"""
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 禁用系统代理（解决连接问题）
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(var, None)
os.environ['NO_PROXY'] = '*'

from parsers.markdown_parser import parse_markdown
from agents.workflow import run_workflow, AgentState
from automation.allure_reporter import AllureReporter
from utils.project_paths import (
    OUTPUT_DIR,
    GENERATED_TESTS_DIR,
    LEGACY_GENERATED_TESTS_DIR,
    ALLURE_RESULTS_DIR,
    ALLURE_REPORT_DIR,
    PLAYWRIGHT_RESULTS_DIR,
)


def get_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.now().strftime("(%Y-%m-%d_%H-%M-%S)")


def clean_history_data():
    """清理历史数据"""
    output_dir = OUTPUT_DIR
    tests_dir = GENERATED_TESTS_DIR
    allure_results_dir = ALLURE_RESULTS_DIR
    allure_report_dir = ALLURE_REPORT_DIR
    test_results_dir = PLAYWRIGHT_RESULTS_DIR

    if output_dir.exists():
        print("  [清理] output 目录...")
        for file in output_dir.iterdir():
            if file.is_file():
                file.unlink()
                print(f"    - 删除: {file.name}")

    if tests_dir.exists():
        print(f"  [清理] {tests_dir} 目录...")
        for file in tests_dir.glob("*.spec.ts"):
            file.unlink()
            print(f"    - 删除: {file.name}")

    if LEGACY_GENERATED_TESTS_DIR.exists():
        print("  [清理] tests/generated 旧目录...")
        for file in LEGACY_GENERATED_TESTS_DIR.glob("*.spec.ts"):
            file.unlink()
            print(f"    - 删除: {file.name}")

    # 清理 Allure 与 Playwright 运行产物，避免历史结果污染当前报告
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


def save_results(state: AgentState, timestamp: str):
    """保存工作流结果"""
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存需求分析结果
    requirements = state.get("requirements", [])
    if requirements:
        requirements_file = output_dir / f"requirements{timestamp}.json"
        with open(requirements_file, "w", encoding="utf-8") as f:
            json.dump({"requirements": requirements}, f, ensure_ascii=False, indent=2)
        print(f"  需求分析: {requirements_file}")

    # 保存测试用例
    test_cases = state.get("test_cases", [])
    if test_cases:
        test_cases_file = output_dir / f"test_cases{timestamp}.json"
        with open(test_cases_file, "w", encoding="utf-8") as f:
            json.dump({"test_cases": test_cases}, f, ensure_ascii=False, indent=2)
        print(f"  测试用例: {test_cases_file}")

    # 保存评审结果
    review_comments = state.get("review_comments", [])
    review_suggestions = state.get("review_suggestions", [])
    review_score = state.get("review_score")

    if review_comments or review_suggestions:
        review_file = output_dir / f"review{timestamp}.json"
        with open(review_file, "w", encoding="utf-8") as f:
            json.dump({
                "passed": state.get("review_passed"),
                "score": review_score,
                "comments": review_comments,
                "suggestions": review_suggestions
            }, f, ensure_ascii=False, indent=2)
        print(f"  评审结果: {review_file}")

    # 保存执行结果（阶段3新增）
    exec_results = state.get("execution_results")
    if exec_results:
        exec_file = output_dir / f"execution{timestamp}.json"
        with open(exec_file, "w", encoding="utf-8") as f:
            json.dump(exec_results, f, ensure_ascii=False, indent=2)
        print(f"  执行结果: {exec_file}")


def print_summary(state: AgentState, timestamp: str):
    """打印执行摘要"""
    print("\n" + "=" * 60)
    print("Agent 协作工作流完成")
    print("=" * 60)

    print(f"\n生成时间: {timestamp}")
    print(f"\n执行统计:")
    print(f"  - 需求数量: {len(state.get('requirements', []))}")
    print(f"  - 用例数量: {len(state.get('test_cases', []))}")
    print(f"  - 评审得分: {state.get('review_score', 'N/A')}/100")
    print(f"  - 迭代次数: {state.get('iteration_count', 0)}")
    print(f"  - 评审通过: {'是' if state.get('review_passed') else '否'}")

    # 阶段3新增：脚本和执行信息
    print(f"\n脚本与执行:")
    print(f"  - 生成脚本: {state.get('generated_script', 'N/A')}")

    exec_results = state.get("execution_results")
    if exec_results:
        print(f"  - 执行状态: {exec_results.get('status')}")
        print(f"  - 测试总数: {exec_results.get('total')}")
        print(f"  - 通过数量: {exec_results.get('passed')}")
        print(f"  - 失败数量: {exec_results.get('failed')}")
        print(f"  - 执行耗时: {exec_results.get('duration')}秒")

        # 计算通过率
        if exec_results.get('total', 0) > 0:
            pass_rate = exec_results['passed'] / exec_results['total'] * 100
            print(f"  - 通过率: {pass_rate:.1f}%")

    # Allure 报告
    allure_path = state.get("allure_report_path")
    if allure_path:
        print(f"\n测试报告:")
        print(f"  - Allure 报告: {allure_path}")
        print(f"  - 查看命令: allure open {allure_path}")

    # 显示评审建议
    suggestions = state.get("review_suggestions", [])
    if suggestions:
        print(f"\n改进建议:")
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"  {i}. {suggestion}")
        if len(suggestions) > 5:
            print(f"  ... 还有 {len(suggestions) - 5} 条建议")

    # 显示 Agent 消息
    messages = state.get("agent_messages", [])
    if messages:
        print(f"\nAgent 消息:")
        for msg in messages[-5:]:  # 只显示最后5条
            if isinstance(msg, dict):
                print(f"  [{msg.get('role', 'unknown')}]: {msg.get('content', '')}")

    print("\n输出文件:")
    print(f"  1. 测试用例: output/test_cases{timestamp}.json")
    print(f"  2. 评审结果: output/review{timestamp}.json")
    if exec_results:
        print(f"  3. 执行结果: output/execution{timestamp}.json")


def main():
    """主流程 - 阶段3"""
    load_dotenv()

    print("=" * 60)
    print("AI测试自动化平台 - 阶段3: 完整自动化流程")
    print("=" * 60)

    # 0. 清理历史数据
    print("\n[步骤0] 清理历史数据...")
    clean_history_data()

    timestamp = get_timestamp()

    # 1. 读取需求文档
    print("\n[步骤1] 读取需求文档...")
    requirement_file = "examples/requirement_baidu.md"

    if not os.path.exists(requirement_file):
        print(f"错误: 需求文档不存在 {requirement_file}")
        return

    requirement_text = parse_markdown(requirement_file)
    print(f"[OK] 需求文档读取成功 ({len(requirement_text)} 字符)")

    # 2. 运行 Agent 协作工作流（包含脚本生成和测试执行）
    print("\n[步骤2] 启动完整工作流...")
    print("-" * 60)

    try:
        final_state = run_workflow(
            requirement_text=requirement_text,
            max_iterations=2,
            page_url="https://www.baidu.com"  # 可根据实际项目修改，如登录页面地址
        )
    except Exception as e:
        print(f"[FAIL] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 保存结果
    print("\n[步骤3] 保存结果...")
    save_results(final_state, timestamp)

    # 4. 打印摘要
    print_summary(final_state, timestamp)

    # 5. 自动打开 Allure 报告
    print("\n[步骤4] 打开测试报告...")
    open_allure_report()


def open_allure_report():
    """生成并打开 Allure HTML 报告"""
    reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")

    # 检查 Allure 是否安装
    if not reporter.check_allure_installed():
        print("  [WARN] Allure 未安装，无法生成报告")
        print("  安装命令: npm install -g allure-commandline")
        return

    # 检查是否有测试结果
    if not reporter.results_dir.exists():
        print("  [WARN] 没有测试结果，无法生成报告")
        return

    # 生成静态 HTML 报告
    print("  [INFO] 正在生成 Allure HTML 报告...")
    result = reporter.generate_report()

    if result["status"] == "success":
        print(f"  [OK] 报告已生成: {result['report_path']}")
        open_result = reporter.open_report()
        if open_result["status"] == "success":
            print(f"  [OK] 报告服务地址: {open_result['url']}")
        else:
            print(f"  [WARN] 报告已生成，但启动本地服务失败: {open_result['error']}")
    else:
        print(f"  [FAIL] 报告生成失败: {result['error']}")


if __name__ == "__main__":
    main()
