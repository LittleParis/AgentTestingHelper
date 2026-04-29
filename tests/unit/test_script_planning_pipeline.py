from unittest.mock import MagicMock, patch

from core.automation.script_plan_validator import PlanValidator
from core.automation.script_planning_agent import ScriptPlanningAgent
from core.automation.script_renderer import ScriptRenderer
from core.models.script_plan import ExecutionTarget, ScriptExecutionPlan


SAMPLE_CASE = {
    "id": "TC_001_001",
    "requirement_id": "REQ_001",
    "title": "Login succeeds with valid credentials",
    "type": "functional",
    "steps": [
        {"step_number": 1, "action": "Open login page", "expected": "Login page is visible"},
        {"step_number": 2, "action": "输入用户名", "data": "", "expected": "用户名输入框显示已输入内容"},
        {"step_number": 3, "action": "输入密码", "data": "", "expected": "密码输入框显示已输入内容"},
        {"step_number": 4, "action": "点击登录按钮", "expected": "登录请求提交成功"},
    ],
    "expected": "仍停留在登录页，未跳转到主界面",
}

SAMPLE_STRATEGY_CONTEXT = {
    "execution_mode": "deep",
    "requirement_strategy": {
        "requirement_id": "REQ_001",
        "overall_risk": "high",
    },
    "focus_points": [
        {
            "point_id": "REQ_001_P01",
            "point_text": "A valid username and password should log in successfully.",
            "focus_level": "major",
            "execution_mode": "deep",
        }
    ],
}


def test_planning_agent_builds_valid_structured_plan_without_llm():
    agent = ScriptPlanningAgent(use_llm=False)

    plan = agent.plan(
        SAMPLE_CASE,
        strategy_context=SAMPLE_STRATEGY_CONTEXT,
        scenario_config={"credentials": {"username_env": "LOGIN_USERNAME", "password_env": "LOGIN_PASSWORD"}},
        page_url="https://example.com/login",
    )

    assert isinstance(plan, ScriptExecutionPlan)
    assert plan.testcase_id == "TC_001_001"
    assert plan.scenario.scenario_type == "login"
    assert plan.setup.required_env_vars == ["LOGIN_USERNAME", "LOGIN_PASSWORD"]
    assert any(step.preferred_executor in {ExecutionTarget.PLAYWRIGHT_NATIVE, ExecutionTarget.MIXED} for step in plan.steps)


def test_validator_repairs_missing_assertions_and_applies_login_only_safety():
    agent = ScriptPlanningAgent(use_llm=False)
    validator = PlanValidator()

    plan = agent.plan(
        {
            "id": "TC_LOGIN_ONLY",
            "title": "Restricted login verification",
            "type": "functional",
            "steps": [{"action": "Submit credentials", "expected": ""}],
            "expected": "LianLian logo is visible",
        },
        strategy_context={},
        scenario_config={
            "scenario_type": "login_only",
            "success_signal": {"type": "visual_text_or_logo", "value": "LianLian"},
            "forbidden_actions": ["navigation_after_login"],
        },
        page_url="https://global.lianlianpay.com/signin",
    )

    plan.steps[0].assertion_intents = []
    repaired = validator.validate(
        plan,
        scenario_config={
            "scenario_type": "login_only",
            "success_signal": {"type": "visual_text_or_logo", "value": "LianLian"},
            "forbidden_actions": ["navigation_after_login"],
        },
        tc_title="Restricted login verification",
        steps=[{"action": "Submit credentials", "expected": ""}],
    )

    assert repaired.scenario.scenario_type == "login_only"
    assert "stop_after_login_success" in repaired.scenario.safety_constraints
    assert "navigation_after_login" in repaired.setup.safety_constraints
    assert repaired.final_assertions


def test_renderer_is_stable_for_same_plan():
    agent = ScriptPlanningAgent(use_llm=False)
    renderer = ScriptRenderer()
    plan = agent.plan(
        SAMPLE_CASE,
        strategy_context=SAMPLE_STRATEGY_CONTEXT,
        scenario_config={"credentials": {"username_env": "LOGIN_USERNAME", "password_env": "LOGIN_PASSWORD"}},
        page_url="https://example.com/login",
    )

    script_one = renderer.render([plan])
    script_two = renderer.render([plan])

    assert script_one.split("import { test as base, expect }", 1)[1] == script_two.split("import { test as base, expect }", 1)[1]
    assert 'const runtimeUsername = process.env["LOGIN_USERNAME"] ?? \'\';' in script_one
    assert "await identifierInput.fill(runtimeUsername ||" in script_one


@patch("core.automation.script_planning_agent.get_llm_client")
def test_planning_agent_falls_back_when_llm_returns_invalid_payload(mock_get_client):
    mock_client = MagicMock()
    mock_client.invoke_structured.side_effect = RuntimeError("bad llm payload")
    mock_get_client.return_value = mock_client

    agent = ScriptPlanningAgent(use_llm=True)
    plan = agent.plan(
        SAMPLE_CASE,
        strategy_context=SAMPLE_STRATEGY_CONTEXT,
        scenario_config={"credentials": {"username_env": "LOGIN_USERNAME", "password_env": "LOGIN_PASSWORD"}},
        page_url="https://example.com/login",
    )

    assert plan.metadata["source"] == "deterministic_baseline"
    assert "llm_planning_error" in plan.metadata


def test_strategy_context_changes_execution_policy_and_step_executor():
    smoke_agent = ScriptPlanningAgent(use_llm=False)
    deep_agent = ScriptPlanningAgent(use_llm=False)

    smoke_plan = smoke_agent.plan(
        SAMPLE_CASE,
        strategy_context={"execution_mode": "smoke", "requirement_strategy": {"overall_risk": "low"}},
        scenario_config={"credentials": {"username_env": "LOGIN_USERNAME", "password_env": "LOGIN_PASSWORD"}},
        page_url="https://example.com/login",
    )
    deep_plan = deep_agent.plan(
        SAMPLE_CASE,
        strategy_context=SAMPLE_STRATEGY_CONTEXT,
        scenario_config={"credentials": {"username_env": "LOGIN_USERNAME", "password_env": "LOGIN_PASSWORD"}},
        page_url="https://example.com/login",
    )

    assert smoke_plan.scenario.execution_policy.value == "native_first"
    assert deep_plan.scenario.execution_policy.value == "hybrid_balanced"


def test_renderer_declares_login_only_masked_fields_outside_try_scope():
    agent = ScriptPlanningAgent(use_llm=False)
    renderer = ScriptRenderer()

    plan = agent.plan(
        {
            "id": "TC_LOGIN_ONLY",
            "title": "Restricted login verification",
            "type": "functional",
            "steps": [{"step_number": 1, "action": "Submit credentials", "expected": "LianLian logo is visible"}],
            "expected": "LianLian logo is visible",
        },
        strategy_context={},
        scenario_config={
            "scenario_type": "login_only",
            "credentials": {"username_env": "LOGIN_USERNAME", "password_env": "LOGIN_PASSWORD"},
            "success_signal": {"type": "visual_text_or_logo", "value": "LianLian"},
        },
        page_url="https://global.lianlianpay.com/signin",
    )

    script = renderer.render([plan])

    assert "let maskedFields = [];\n    try {" in script
    assert "await attachFinalScreenshot(page, testInfo, { mask: maskedFields });" in script
