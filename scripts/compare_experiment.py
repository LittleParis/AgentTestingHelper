"""
对比实验：验证评审反馈注入生成器的效果

实验设计：
1. 使用一个评审容易不通过的需求（边界条件少、异常场景缺失）
2. 第一次生成 -> 评审 -> 记录问题
3. 第二次生成（带改进提示）-> 评审 -> 对比得分变化
4. 分析改进建议是否被采纳
"""
import sys
import os

# 清除代理设置（解决连接问题）
for _var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(_var, None)
os.environ['NO_PROXY'] = '*'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.agents.test_case_generator import TestCaseGenerator
from core.agents.case_reviewer import CaseReviewer
from core.models.requirement import Requirement, Priority, RequirementType


def run_comparison_experiment():
    """运行对比实验"""

    # 使用一个简单的需求，容易导致评审不通过
    requirement_text = """
# 用户登录功能

## 功能描述
用户可以通过邮箱和密码登录系统。

## 验收标准
1. 正确的邮箱和密码可以成功登录
2. 错误的密码提示"密码错误"
"""

    print("=" * 70)
    print("评审反馈注入生成器 - 对比实验")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: 需求分析
    print("[Step 1] 需求分析...")
    analyzer = RequirementAnalyzer()
    analysis_result = analyzer.analyze(requirement_text)
    requirements = analysis_result.get("requirements", [])
    print(f"  识别到 {len(requirements)} 个需求")
    for req in requirements:
        print(f"    - {req['id']}: {req['title']}")
    print()

    # Step 2: 第一次生成（无改进提示）
    print("[Step 2] 第一次生成测试用例（无改进提示）...")
    generator = TestCaseGenerator()
    first_test_cases = []
    for req in requirements:
        tcs = generator.generate(req)
        first_test_cases.extend(tcs)
        print(f"  {req['id']}: 生成 {len(tcs)} 个用例")
    print(f"  总计: {len(first_test_cases)} 个用例")
    print()

    # Step 3: 第一次评审
    print("[Step 3] 第一次评审...")
    reviewer = CaseReviewer()
    first_review = reviewer.review_all(requirements, first_test_cases)
    first_score = first_review.get("total_score", 0)
    first_passed = first_review.get("passed", False)
    first_suggestions = first_review.get("details", [])[0].get("suggestions", []) if first_review.get("details") else []

    print(f"  评审得分: {first_score}/100")
    print(f"  是否通过: {'通过' if first_passed else '未通过'}")
    print(f"  改进建议 ({len(first_suggestions)} 条):")
    for i, s in enumerate(first_suggestions[:5], 1):
        print(f"    {i}. {s}")
    if len(first_suggestions) > 5:
        print(f"    ... 还有 {len(first_suggestions) - 5} 条")
    print()

    # Step 4: 第二次生成（带改进提示）
    print("[Step 4] 第二次生成测试用例（带改进提示）...")
    print(f"  注入 {len(first_suggestions)} 条改进建议")

    second_test_cases = []
    for req in requirements:
        tcs = generator.generate(req, improvement_hints=first_suggestions)
        second_test_cases.extend(tcs)
        print(f"  {req['id']}: 生成 {len(tcs)} 个用例")
    print(f"  总计: {len(second_test_cases)} 个用例")
    print()

    # Step 5: 第二次评审
    print("[Step 5] 第二次评审...")
    second_review = reviewer.review_all(requirements, second_test_cases)
    second_score = second_review.get("total_score", 0)
    second_passed = second_review.get("passed", False)
    second_suggestions = second_review.get("details", [])[0].get("suggestions", []) if second_review.get("details") else []

    print(f"  评审得分: {second_score}/100")
    print(f"  是否通过: {'通过' if second_passed else '未通过'}")
    print(f"  改进建议 ({len(second_suggestions)} 条):")
    for i, s in enumerate(second_suggestions[:5], 1):
        print(f"    {i}. {s}")
    if len(second_suggestions) > 5:
        print(f"    ... 还有 {len(second_suggestions) - 5} 条")
    print()

    # Step 6: 对比分析
    print("=" * 70)
    print("对比分析结果")
    print("=" * 70)

    score_change = second_score - first_score
    suggestions_change = len(first_suggestions) - len(second_suggestions)

    print(f"\n{'指标':<20} {'第一次':<15} {'第二次':<15} {'变化':<15}")
    print("-" * 65)
    print(f"{'评审得分':<20} {first_score:<15.1f} {second_score:<15.1f} {score_change:+.1f}")
    print(f"{'是否通过':<20} {'是' if first_passed else '否':<15} {'是' if second_passed else '否':<15} {'[改进]' if second_passed and not first_passed else ''}")
    print(f"{'用例数量':<20} {len(first_test_cases):<15} {len(second_test_cases):<15} {len(second_test_cases) - len(first_test_cases):+d}")
    print(f"{'改进建议数':<20} {len(first_suggestions):<15} {len(second_suggestions):<15} {suggestions_change:+d}")

    # 分析用例变化
    print("\n" + "-" * 65)
    print("用例标题对比:")
    print("-" * 65)

    first_titles = set(tc['title'] for tc in first_test_cases)
    second_titles = set(tc['title'] for tc in second_test_cases)

    new_titles = second_titles - first_titles
    removed_titles = first_titles - second_titles

    if new_titles:
        print(f"\n新增用例 ({len(new_titles)}):")
        for title in sorted(new_titles):
            print(f"  + {title}")

    if removed_titles:
        print(f"\n移除用例 ({len(removed_titles)}):")
        for title in sorted(removed_titles):
            print(f"  - {title}")

    # 结论
    print("\n" + "=" * 70)
    print("实验结论")
    print("=" * 70)

    if score_change > 0:
        print(f"[OK] 评审得分提升了 {score_change:.1f} 分")
        print("   说明改进提示有效地指导了用例生成")
    elif score_change == 0:
        print("[WARN] 评审得分没有变化")
        print("   可能需要检查改进提示是否被正确理解")
    else:
        print(f"[FAIL] 评审得分下降了 {abs(score_change):.1f} 分")
        print("   需要调查原因")

    if suggestions_change > 0:
        print(f"[OK] 改进建议减少了 {suggestions_change} 条")
        print("   说明部分问题已被解决")
    elif suggestions_change == 0:
        print("[WARN] 改进建议数量没有变化")

    if second_passed and not first_passed:
        print("[OK] 评审从「未通过」变为「通过」")
        print("   改进提示成功帮助通过了评审")

    return {
        "first_score": first_score,
        "second_score": second_score,
        "score_change": score_change,
        "first_passed": first_passed,
        "second_passed": second_passed,
        "suggestions_change": suggestions_change
    }


if __name__ == "__main__":
    result = run_comparison_experiment()
