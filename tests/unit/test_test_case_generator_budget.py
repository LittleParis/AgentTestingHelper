from unittest.mock import MagicMock

from core.agents.test_case_generator import TestCaseGenerator
from core.models.test_case import TestCase, TestCaseGenerationResult, TestStep


def _make_test_case(case_id: str, requirement_id: str, title: str) -> TestCase:
    return TestCase(
        id=case_id,
        requirement_id=requirement_id,
        title=title,
        steps=[TestStep(step_number=1, action="Open page", expected="Page is visible")],
        expected="Flow completes successfully",
    )


def test_generation_context_trims_case_count_and_normalizes_ids():
    generator = TestCaseGenerator()
    generator.llm = MagicMock()
    generator.llm.invoke_structured.return_value = TestCaseGenerationResult(
        test_cases=[
            _make_test_case("TC_001", "REQ_001", "Case 1"),
            _make_test_case("TC_002", "REQ_001", "Case 2"),
            _make_test_case("TC_003", "REQ_001", "Case 3"),
        ],
        requirement_id="REQ_001",
        total_count=3,
    )

    requirement = {
        "id": "REQ_001",
        "title": "登录流程",
        "description": "用户可以完成登录并进入首页。",
        "priority": "high",
        "type": "functional",
        "acceptance_criteria": ["用户可以成功登录系统。"],
        "ui_elements": ["用户名输入框", "密码输入框", "登录按钮"],
        "generation_context": {
            "planning_mode": "strategy",
            "flow_name": "登录",
            "flow_type": "setup",
            "overall_risk": "medium",
            "target_case_count": 1,
            "coverage_focus": ["happy_path"],
            "planning_reason": "Setup flow should stay compact.",
            "focus_points": [
                {
                    "point_id": "REQ_001_P01",
                    "point_text": "用户可以成功登录系统。",
                    "focus_level": "major",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path"],
                    "reason": "Main login success path",
                    "case_weight": 2,
                }
            ],
            "case_id_prefix": "001",
        },
    }

    cases = generator.generate(requirement)

    assert len(cases) == 1
    assert cases[0]["id"] == "TC_001_001"
    assert cases[0]["requirement_id"] == "REQ_001"


def test_generation_context_is_reflected_in_prompt():
    generator = TestCaseGenerator()
    prompt = generator._build_prompt(
        requirement=generator._dict_to_requirement(
            {
                "id": "REQ_002",
                "title": "支付流程",
                "description": "用户可以完成支付并处理失败场景。",
                "priority": "high",
                "type": "functional",
                "acceptance_criteria": ["支付成功后展示结果。"],
                "ui_elements": ["支付按钮"],
            }
        ),
        generation_context={
            "planning_mode": "strategy",
            "flow_name": "支付",
            "flow_type": "payment",
            "overall_risk": "critical",
            "target_case_count": 3,
            "coverage_focus": ["happy_path", "negative", "boundary"],
            "planning_reason": "Payment is high-risk.",
            "focus_points": [
                {
                    "point_id": "REQ_002_P01",
                    "point_text": "支付失败允许重试",
                    "focus_level": "critical",
                    "execution_mode": "deep",
                    "coverage_axes": ["happy_path", "negative", "recovery"],
                    "reason": "High-risk payment retry flow",
                    "case_weight": 3,
                }
            ],
            "case_id_prefix": "002",
        },
    )

    assert '"target_case_count": 3' in prompt
    assert '"coverage_focus": [' in prompt
    assert "Cover critical focus points first" in prompt
    assert "You must generate exactly 3 test cases" in prompt
