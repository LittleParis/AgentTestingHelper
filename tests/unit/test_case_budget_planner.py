from core.agents.case_budget_planner import CaseBudgetPlanner


def _make_requirement(
    requirement_id: str,
    title: str,
    description: str,
    acceptance_criteria: list[str],
) -> dict:
    return {
        "id": requirement_id,
        "title": title,
        "description": description,
        "priority": "high",
        "type": "functional",
        "acceptance_criteria": acceptance_criteria,
        "ui_elements": [],
    }


def _make_strategy(
    requirement_id: str,
    *,
    overall_risk: str,
    suggested_case_budget: int,
    focus_points: list[dict],
) -> dict:
    return {
        "requirement_id": requirement_id,
        "overall_risk": overall_risk,
        "suggested_case_budget": suggested_case_budget,
        "strategy_summary": f"Strategy for {requirement_id}",
        "focus_points": focus_points,
    }


def _make_focus_point(
    point_id: str,
    point_text: str,
    *,
    focus_level: str,
    execution_mode: str,
    coverage_axes: list[str],
    case_weight: int,
) -> dict:
    return {
        "point_id": point_id,
        "point_text": point_text,
        "focus_level": focus_level,
        "execution_mode": execution_mode,
        "coverage_axes": coverage_axes,
        "reason": f"{point_text} reason",
        "case_weight": case_weight,
    }


def test_login_strategy_keeps_budget_small_and_merges_light_points():
    planner = CaseBudgetPlanner()
    analyzed_requirements = [
        _make_requirement(
            "REQ_001",
            "登录流程",
            "用户可以使用有效账号密码登录。",
            ["登录页加载并展示输入控件", "提交有效账号密码后登录成功"],
        )
    ]
    strategy_plan = {
        "overall_summary": "Login strategy summary",
        "total_suggested_case_budget": 1,
        "requirement_strategies": [
            _make_strategy(
                "REQ_001",
                overall_risk="medium",
                suggested_case_budget=1,
                focus_points=[
                    _make_focus_point(
                        "REQ_001_P01",
                        "登录页加载并展示输入控件",
                        focus_level="light",
                        execution_mode="smoke",
                        coverage_axes=["happy_path"],
                        case_weight=1,
                    ),
                    _make_focus_point(
                        "REQ_001_P02",
                        "提交有效账号密码后登录成功",
                        focus_level="major",
                        execution_mode="standard",
                        coverage_axes=["happy_path"],
                        case_weight=2,
                    ),
                ],
            )
        ],
    }

    planned = planner.plan(
        requirement_text="# Login",
        analyzed_requirements=analyzed_requirements,
        strategy_plan=strategy_plan,
        page_url="https://example.com/login",
    )

    assert len(planned) == 1
    assert planned[0]["flow_type"] == "setup"
    assert planned[0]["generation_context"]["target_case_count"] == 1
    # Verify focus_points contains the light point
    focus_points = planned[0]["generation_context"]["focus_points"]
    light_points = [p for p in focus_points if p.get("focus_level") == "light"]
    assert len(light_points) == 1
    assert light_points[0]["point_id"] == "REQ_001_P01"


def test_brand_pay_domain_does_not_change_login_flow_type_when_strategy_is_login():
    planner = CaseBudgetPlanner()
    analyzed_requirements = [
        _make_requirement(
            "REQ_001",
            "登录流程",
            "用户输入账号密码后登录成功。",
            ["提交有效账号密码后登录成功"],
        )
    ]
    strategy_plan = {
        "overall_summary": "Login strategy summary",
        "total_suggested_case_budget": 1,
        "requirement_strategies": [
            _make_strategy(
                "REQ_001",
                overall_risk="medium",
                suggested_case_budget=1,
                focus_points=[
                    _make_focus_point(
                        "REQ_001_P01",
                        "提交有效账号密码后登录成功",
                        focus_level="major",
                        execution_mode="standard",
                        coverage_axes=["happy_path"],
                        case_weight=2,
                    )
                ],
            )
        ],
    }

    planned = planner.plan(
        requirement_text="https://global.lianlianpay.com/signin",
        analyzed_requirements=analyzed_requirements,
        strategy_plan=strategy_plan,
    )

    assert [item["flow_type"] for item in planned] == ["setup"]


def test_mixed_document_uses_strategy_weights_and_adds_e2e_case():
    planner = CaseBudgetPlanner()
    analyzed_requirements = [
        _make_requirement("REQ_001", "登录流程", "用户完成登录。", ["提交有效账号密码后登录成功"]),
        _make_requirement("REQ_002", "下单流程", "用户创建订单并提交。", ["提交订单成功并生成订单结果"]),
        _make_requirement("REQ_003", "支付流程", "用户完成支付。", ["支付成功展示结果", "支付失败允许重试"]),
    ]
    strategy_plan = {
        "overall_summary": "Mixed strategy summary",
        "total_suggested_case_budget": 6,
        "requirement_strategies": [
            _make_strategy(
                "REQ_001",
                overall_risk="low",
                suggested_case_budget=1,
                focus_points=[
                    _make_focus_point(
                        "REQ_001_P01",
                        "提交有效账号密码后登录成功",
                        focus_level="light",
                        execution_mode="smoke",
                        coverage_axes=["happy_path"],
                        case_weight=1,
                    )
                ],
            ),
            _make_strategy(
                "REQ_002",
                overall_risk="medium",
                suggested_case_budget=1,
                focus_points=[
                    _make_focus_point(
                        "REQ_002_P01",
                        "提交订单成功并生成订单结果",
                        focus_level="normal",
                        execution_mode="standard",
                        coverage_axes=["happy_path"],
                        case_weight=1,
                    )
                ],
            ),
            _make_strategy(
                "REQ_003",
                overall_risk="critical",
                suggested_case_budget=3,
                focus_points=[
                    _make_focus_point(
                        "REQ_003_P01",
                        "支付成功展示结果",
                        focus_level="major",
                        execution_mode="standard",
                        coverage_axes=["happy_path"],
                        case_weight=2,
                    ),
                    _make_focus_point(
                        "REQ_003_P02",
                        "支付失败允许重试",
                        focus_level="critical",
                        execution_mode="deep",
                        coverage_axes=["happy_path", "negative", "recovery"],
                        case_weight=3,
                    ),
                ],
            ),
        ],
    }

    planned = planner.plan(
        requirement_text="# Checkout Journey",
        analyzed_requirements=analyzed_requirements,
        strategy_plan=strategy_plan,
        page_url="https://example.com/app",
    )

    assert len(planned) == 4
    budgets = {
        requirement["flow_type"]: requirement["generation_context"]["target_case_count"]
        for requirement in planned
    }
    assert budgets["setup"] == 1
    assert budgets["core_business"] == 1
    assert budgets["payment"] >= 3
    assert budgets["e2e"] == 1


def test_payment_risk_document_increases_payment_budget_from_strategy():
    planner = CaseBudgetPlanner()
    analyzed_requirements = [
        _make_requirement(
            "REQ_001",
            "支付流程",
            "用户发起支付并处理失败重试。",
            ["支付成功展示结果", "支付失败允许重试并保持结果一致"],
        )
    ]
    strategy_plan = {
        "overall_summary": "Payment strategy summary",
        "total_suggested_case_budget": 3,
        "requirement_strategies": [
            _make_strategy(
                "REQ_001",
                overall_risk="critical",
                suggested_case_budget=3,
                focus_points=[
                    _make_focus_point(
                        "REQ_001_P01",
                        "支付成功展示结果",
                        focus_level="major",
                        execution_mode="standard",
                        coverage_axes=["happy_path"],
                        case_weight=2,
                    ),
                    _make_focus_point(
                        "REQ_001_P02",
                        "支付失败允许重试并保持结果一致",
                        focus_level="critical",
                        execution_mode="deep",
                        coverage_axes=["happy_path", "negative", "recovery"],
                        case_weight=3,
                    ),
                ],
            )
        ],
    }

    planned = planner.plan(
        requirement_text="# Payment",
        analyzed_requirements=analyzed_requirements,
        strategy_plan=strategy_plan,
    )

    assert len(planned) == 1
    assert planned[0]["flow_type"] == "payment"
    assert planned[0]["generation_context"]["target_case_count"] >= 3
    assert "negative" in planned[0]["generation_context"]["coverage_focus"]
