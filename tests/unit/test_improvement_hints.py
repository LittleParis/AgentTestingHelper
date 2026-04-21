"""测试评审反馈注入生成器功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.test_case_generator import TestCaseGenerator
from core.models.requirement import Requirement, Priority, RequirementType


def test_improvement_hints():
    """测试改进提示是否被正确注入到 prompt 中"""
    generator = TestCaseGenerator()

    requirement = Requirement(
        id="REQ_001",
        title="用户登录",
        description="用户可以通过用户名和密码登录系统",
        priority=Priority.HIGH,
        type=RequirementType.FUNCTIONAL,
        acceptance_criteria=[
            "正确的用户名和密码可以成功登录",
            "错误的密码提示'密码错误'"
        ]
    )

    # 测试无改进提示时的 prompt
    prompt_without_hints = generator._build_prompt(requirement)
    print("=" * 60)
    print("无改进提示时的 Prompt:")
    print("=" * 60)
    print(prompt_without_hints[:500])
    print("...")

    # 测试有改进提示时的 prompt
    improvement_hints = [
        "增加密码为空的边界测试",
        "添加账号锁定场景测试",
        "TC_001 缺少预期结果"
    ]

    prompt_with_hints = generator._build_prompt(requirement, improvement_hints)
    print("\n" + "=" * 60)
    print("有改进提示时的 Prompt:")
    print("=" * 60)
    print(prompt_with_hints[:800])
    print("...")

    # 验证改进提示是否被注入
    assert "上次评审发现的问题" in prompt_with_hints, "改进提示部分未找到"
    assert "增加密码为空的边界测试" in prompt_with_hints, "改进提示内容未找到"
    assert "上次评审发现的问题" not in prompt_without_hints, "无改进提示时不应该有该部分"

    print("\n" + "=" * 60)
    print("✅ 测试通过：改进提示已正确注入到 prompt 中")
    print("=" * 60)


def test_generate_with_hints():
    """测试带改进提示的生成功能（需要 LLM 调用）"""
    print("\n" + "=" * 60)
    print("测试带改进提示的生成功能")
    print("=" * 60)

    generator = TestCaseGenerator()

    requirement = Requirement(
        id="REQ_001",
        title="用户登录",
        description="用户可以通过用户名和密码登录系统",
        priority=Priority.HIGH,
        type=RequirementType.FUNCTIONAL,
        acceptance_criteria=[
            "正确的用户名和密码可以成功登录",
            "错误的密码提示'密码错误'"
        ]
    )

    improvement_hints = [
        "增加密码为空的边界测试",
        "添加账号锁定场景测试"
    ]

    print("\n[INFO] 第一次生成（无改进提示）...")
    result1 = generator.generate_structured(requirement)
    print(f"  生成 {len(result1.test_cases)} 个测试用例")
    for tc in result1.test_cases:
        print(f"    - {tc.id}: {tc.title}")

    print("\n[INFO] 第二次生成（带改进提示）...")
    result2 = generator.generate_structured(requirement, improvement_hints)
    print(f"  生成 {len(result2.test_cases)} 个测试用例")
    for tc in result2.test_cases:
        print(f"    - {tc.id}: {tc.title}")

    print("\n✅ 生成功能测试完成")


if __name__ == "__main__":
    test_improvement_hints()
    # test_generate_with_hints()  # 取消注释以测试实际 LLM 调用
