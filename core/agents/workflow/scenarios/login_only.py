"""Login-only scenario handling."""

from typing import Any, Dict, List, Optional


def is_login_only_scenario(scenario_config: Optional[Dict[str, Any]]) -> bool:
    """Return whether the current workflow should use the bounded login-only path."""
    return (scenario_config or {}).get("scenario_type") == "login_only"


def build_login_only_requirement(scenario_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a single bounded requirement for the login-only scenario."""
    scenario_config = scenario_config or {}
    success_signal = scenario_config.get("success_signal") or {}
    success_value = str(success_signal.get("value") or "LianLian")
    page_url = str(scenario_config.get("page_url") or "登录页")

    return {
        "id": "REQ_001",
        "title": "受限登录验证",
        "description": (
            f"仅验证用户能否从登录页面 {page_url} 完成受限登录流程，"
            "遇到额外验证时等待人工处理，在检测到成功标志后立即停止。"
        ),
        "priority": "high",
        "type": "functional",
        "acceptance_criteria": [
            "登录页面能够正常加载，并显示用户名输入框、密码输入框和登录按钮。",
            "系统能够使用运行时提供的有效凭证提交登录请求。",
            "如果出现额外验证，自动化流程只等待人工完成，不尝试自动绕过。",
            f"仅当主界面可见 {success_value} 成功标志时，才判定登录成功。",
            "检测到登录成功标志后，自动化流程必须立即停止，不执行任何额外操作。",
        ],
        "ui_elements": ["用户名输入框", "密码输入框", "登录按钮", f"{success_value} 标志"],
        "scenario_type": "login_only",
    }


def build_login_only_test_case(requirement: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single deterministic login-only test case."""
    requirement_id = str(requirement.get("id") or "REQ_001")
    return {
        "id": "TC_001",
        "requirement_id": requirement_id,
        "title": "受限登录主路径验证",
        "priority": "high",
        "type": "ui",
        "steps": [
            {
                "step_number": 1,
                "action": "打开登录页面并等待页面加载完成",
                "expected": "登录页面加载成功，显示登录相关输入元素",
            },
            {
                "step_number": 2,
                "action": "在用户名输入框中填写运行时提供的账号",
                "expected": "用户名输入框成功接收输入内容",
            },
            {
                "step_number": 3,
                "action": "在密码输入框中填写运行时提供的密码",
                "expected": "密码输入框成功接收输入内容",
            },
            {
                "step_number": 4,
                "action": "点击登录按钮提交登录请求",
                "expected": "登录请求提交成功，页面开始处理登录流程",
            },
            {
                "step_number": 5,
                "action": "如出现额外验证则等待用户手动完成验证",
                "expected": "流程等待人工验证完成，不执行任何绕过操作",
            },
            {
                "step_number": 6,
                "action": "验证成功标志出现后立即停止自动化流程",
                "expected": "成功标志可见，流程终止且不执行额外操作",
            },
        ],
        "expected": "用户完成受限登录验证，成功标志出现后流程立即停止。",
        "tags": ["smoke", "login", "login_only"],
        "preconditions": "登录页可访问，运行环境已注入有效登录凭证。",
        "postconditions": "流程在成功标志出现后停止，不继续执行其他页面操作。",
        "estimated_time": 90,
    }


def review_login_only_test_cases(requirements: List[dict], test_cases: List[dict]) -> dict:
    """Run a bounded deterministic review for login-only scenarios."""
    result = simple_review(requirements, test_cases)
    comments = list(result.get("review_comments") or [])
    score = int(result.get("review_score", 100))
    passed = bool(result.get("review_passed", True))

    if len(test_cases) != 1:
        passed = False
        score -= 20
        comments.append(
            {
                "type": "unexpected_case_count",
                "severity": "high",
                "message": f"Login-only scenario must produce exactly 1 test case, got {len(test_cases)}.",
            }
        )

    if test_cases:
        test_case = test_cases[0]
        if not test_case.get("steps"):
            passed = False
            score -= 20
            comments.append(
                {
                    "type": "missing_steps",
                    "severity": "high",
                    "message": f"{test_case.get('id', 'UNKNOWN_TC')} has no executable steps.",
                }
            )

        tags = set(test_case.get("tags") or [])
        if "login_only" not in tags:
            score -= 10
            comments.append(
                {
                    "type": "missing_login_only_tag",
                    "severity": "medium",
                    "message": f"{test_case.get('id', 'UNKNOWN_TC')} should include the login_only tag.",
                }
            )

    score = max(score, 0)
    passed = passed and score >= 60

    return {
        "review_passed": passed,
        "review_score": score,
        "review_comments": comments,
        "review_suggestions": [],
        "current_step": "reviewed",
        "agent_messages": [
            {
                "role": "reviewer",
                "content": (
                    f"Deterministic login-only review {'passed' if passed else 'failed'} "
                    f"with score {score}/100."
                ),
            }
        ],
    }


def simple_review(requirements: List[dict], test_cases: List[dict]) -> dict:
    """Fallback review when the LLM-based reviewer is unavailable."""
    comments = []
    passed = True
    score = 100

    requirement_ids = {req["id"] for req in requirements if "id" in req}
    test_case_requirement_ids = set()
    for test_case in test_cases:
        test_case_id = test_case.get("id", "")
        if test_case_id.startswith("TC_"):
            parts = test_case_id.split("_")
            if len(parts) > 1:
                test_case_requirement_ids.add(f"REQ_{parts[1]}")

    missing_requirements = requirement_ids - test_case_requirement_ids
    if missing_requirements:
        passed = False
        score -= 20
        comments.append(
            {
                "type": "missing_coverage",
                "severity": "high",
                "message": f"Missing test-case coverage for requirements: {sorted(missing_requirements)}",
            }
        )

    for test_case in test_cases:
        if not test_case.get("expected"):
            score -= 5
            comments.append(
                {
                    "type": "missing_expected",
                    "severity": "medium",
                    "message": f"{test_case.get('id', 'UNKNOWN_TC')} has no expected result.",
                }
            )

    if len(test_cases) < len(requirements):
        passed = False
        score -= 20
        comments.append(
            {
                "type": "insufficient_cases",
                "severity": "high",
                "message": (
                    f"Generated test cases ({len(test_cases)}) are fewer than "
                    f"requirements ({len(requirements)})."
                ),
            }
        )

    score = max(score, 0)

    return {
        "review_passed": passed,
        "review_score": score,
        "review_comments": comments,
        "review_suggestions": [],
        "current_step": "reviewed",
        "agent_messages": [
            {
                "role": "reviewer",
                "content": f"Fallback review {'passed' if passed else 'failed'} with score {score}/100.",
            }
        ],
    }
