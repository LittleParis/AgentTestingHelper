import os
from unittest.mock import MagicMock, patch

from langgraph.types import Overwrite, Send

from core.models.workflow import AgentState
from core.agents.workflow import (
    build_workflow,
    run_workflow,
    should_regenerate,
)
from core.agents.workflow.utils import build_executor_env_overrides
from core.agents.workflow.nodes import (
    analyze_requirements_node,
    execute_tests_node,
    fan_out_requirements,
    finalize_test_case_generation_node,
    generate_report_node,
    generate_script_node,
    generate_test_case_for_requirement_node,
    generate_test_cases_node,
    increment_iteration,
    plan_case_budgets_node,
    plan_script_generation_node,
    plan_test_strategy_node,
    review_test_cases_node,
)

# Alias for backward compatibility with tests
_build_executor_env_overrides = build_executor_env_overrides


SAMPLE_REQUIREMENT_TEXT = """
# Checkout Journey

1. Users log in.
2. Users submit an order.
3. Users complete payment and see the result.
"""

SAMPLE_REQUIREMENTS = [
    {
        "id": "REQ_001",
        "title": "Login",
        "description": "Users can sign in with valid credentials.",
        "priority": "high",
        "type": "functional",
        "acceptance_criteria": [
            "A valid username and password should log in successfully.",
            "The page loads and shows the login form.",
        ],
        "ui_elements": ["username", "password", "submit"],
    },
    {
        "id": "REQ_002",
        "title": "Payment",
        "description": "Users complete payment and handle failures.",
        "priority": "high",
        "type": "functional",
        "acceptance_criteria": [
            "Payment succeeds and shows the result.",
            "Payment failure allows retry.",
        ],
        "ui_elements": ["pay button"],
    },
]

SAMPLE_STRATEGY_PLAN = {
    "overall_summary": "Strategy summary",
    "total_suggested_case_budget": 4,
    "fallback_used": False,
    "requirement_strategies": [
        {
            "requirement_id": "REQ_001",
            "overall_risk": "medium",
            "suggested_case_budget": 1,
            "strategy_summary": "Login stays compact.",
            "focus_points": [
                {
                    "point_id": "REQ_001_P01",
                    "point_text": "A valid username and password should log in successfully.",
                    "focus_level": "major",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path"],
                    "reason": "Primary login success path",
                    "case_weight": 2,
                },
                {
                    "point_id": "REQ_001_P02",
                    "point_text": "The page loads and shows the login form.",
                    "focus_level": "light",
                    "execution_mode": "smoke",
                    "coverage_axes": ["happy_path"],
                    "reason": "Low-risk UI prerequisite",
                    "case_weight": 1,
                },
            ],
        },
        {
            "requirement_id": "REQ_002",
            "overall_risk": "critical",
            "suggested_case_budget": 3,
            "strategy_summary": "Payment gets deeper coverage.",
            "focus_points": [
                {
                    "point_id": "REQ_002_P01",
                    "point_text": "Payment succeeds and shows the result.",
                    "focus_level": "major",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path"],
                    "reason": "Primary payment result",
                    "case_weight": 2,
                },
                {
                    "point_id": "REQ_002_P02",
                    "point_text": "Payment failure allows retry.",
                    "focus_level": "critical",
                    "execution_mode": "deep",
                    "coverage_axes": ["happy_path", "negative", "recovery"],
                    "reason": "High-risk retry flow",
                    "case_weight": 3,
                },
            ],
        },
    ],
}

REQ_001_CASES = [
    {
        "id": "TC_001_001",
        "requirement_id": "REQ_001",
        "title": "Login succeeds with valid credentials",
        "steps": [
            {"step_number": 1, "action": "Open login page", "expected": "Login page is visible"},
            {"step_number": 2, "action": "Submit valid credentials", "expected": "Login succeeds"},
        ],
        "expected": "The user is redirected to the homepage.",
    }
]

REQ_002_CASES = [
    {
        "id": "TC_002_001",
        "requirement_id": "REQ_002",
        "title": "Payment succeeds",
        "steps": [
            {"step_number": 1, "action": "Open payment page", "expected": "Payment page is visible"},
            {"step_number": 2, "action": "Submit payment", "expected": "Payment succeeds"},
        ],
        "expected": "The system shows a successful payment result.",
    },
    {
        "id": "TC_002_002",
        "requirement_id": "REQ_002",
        "title": "Payment retry after failure",
        "steps": [
            {"step_number": 1, "action": "Trigger payment failure", "expected": "Failure is visible"},
            {"step_number": 2, "action": "Retry payment", "expected": "Retry path is available"},
        ],
        "expected": "The retry path preserves payment consistency.",
    },
]


def make_state(**overrides) -> AgentState:
    state: AgentState = {
        "requirement_text": SAMPLE_REQUIREMENT_TEXT,
        "requirements": SAMPLE_REQUIREMENTS,
        "planned_requirements": None,
        "test_strategy": None,
        "requirement_summary": None,
        "test_cases": [],
        "review_passed": None,
        "review_score": None,
        "review_comments": None,
        "review_suggestions": None,
        "iteration_count": 0,
        "max_iterations": 2,
        "feedback": [],
        "generated_script": None,
        "script_plans": None,
        "page_url": "https://example.com/login",
        "scenario_config": None,
        "execution_results": None,
        "allure_report_path": None,
        "current_step": "init",
        "agent_messages": [],
    }
    state.update(overrides)
    return state


class TestAnalyzeRequirementsNode:
    @patch("core.agents.workflow.nodes.requirement_nodes.RequirementAnalyzer")
    def test_analyze_success(self, mock_analyzer_class):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "requirements": SAMPLE_REQUIREMENTS,
            "summary": "Two requirements.",
        }
        mock_analyzer_class.return_value = mock_analyzer

        result = analyze_requirements_node(make_state(requirements=None))

        assert result["requirements"] == SAMPLE_REQUIREMENTS
        assert result["requirement_summary"] == "Two requirements."
        assert result["test_strategy"] is None
        assert result["current_step"] == "requirement_analyzed"
        assert result["agent_messages"][0]["role"] == "analyzer"

    @patch("core.agents.workflow.nodes.requirement_nodes.RequirementAnalyzer")
    def test_analyze_login_only_override_still_uses_requirement_analyzer(self, mock_analyzer_class):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "requirements": SAMPLE_REQUIREMENTS[:1],
            "summary": "Analyzer still runs.",
        }
        mock_analyzer_class.return_value = mock_analyzer

        state = make_state(
            requirements=None,
            scenario_config={
                "scenario_type": "login_only",
                "page_url": "https://global.lianlianpay.com/signin",
                "success_signal": {"value": "LianLian"},
            },
        )

        result = analyze_requirements_node(state)

        assert result["requirements"] == SAMPLE_REQUIREMENTS[:1]
        mock_analyzer.analyze.assert_called_once()


class TestStrategyNode:
    @patch("core.agents.workflow.nodes.planning_nodes.TestStrategyPlanner")
    def test_plan_test_strategy_node_stores_strategy_output(self, mock_planner_class):
        mock_planner = MagicMock()
        mock_planner.plan.return_value = SAMPLE_STRATEGY_PLAN
        mock_planner_class.return_value = mock_planner

        result = plan_test_strategy_node(make_state())

        assert result["test_strategy"] == SAMPLE_STRATEGY_PLAN
        assert result["current_step"] == "test_strategy_planned"
        assert "Planned 2 requirement strategies" in result["agent_messages"][0]["content"]


class TestParallelGenerationNodes:
    def test_generate_dispatch_resets_state_for_parallel_run(self):
        result = generate_test_cases_node(make_state(test_cases=[{"id": "OLD_TC"}]))

        assert isinstance(result["test_cases"], Overwrite)
        assert result["test_cases"].value == []
        assert result["current_step"] == "test_case_generation_dispatched"
        assert "Dispatching" in result["agent_messages"][0]["content"]

    def test_fan_out_returns_one_send_per_requirement(self):
        state = make_state(
            requirements=[
                {**SAMPLE_REQUIREMENTS[0], "generation_context": {"target_case_count": 1}},
                {**SAMPLE_REQUIREMENTS[1], "generation_context": {"target_case_count": 3}},
            ]
        )
        sends = fan_out_requirements(state)

        assert len(sends) == 2
        assert all(isinstance(item, Send) for item in sends)
        assert sends[0].node == "generate_test_case_for_requirement"
        assert sends[0].arg["requirement"]["id"] == "REQ_001"
        assert sends[0].arg["strategy_context"]["target_case_count"] == 1

    @patch("core.agents.workflow.nodes.generation_nodes.TestCaseGenerator")
    def test_generate_single_requirement_uses_embedded_strategy_context(self, mock_generator_class):
        mock_generator = MagicMock()
        mock_generator.generate.return_value = REQ_001_CASES
        mock_generator_class.return_value = mock_generator

        requirement = {
            **SAMPLE_REQUIREMENTS[0],
            "generation_context": {
                "planning_mode": "strategy",
                "target_case_count": 1,
                "case_id_prefix": "001",
            },
        }

        result = generate_test_case_for_requirement_node(
            {
                "requirement": requirement,
                "strategy_context": requirement["generation_context"],
                "improvement_hints": None,
                "iteration_count": 0,
            }
        )

        assert result["test_cases"] == REQ_001_CASES
        assert "REQ_001" in result["agent_messages"][0]["content"]
        mock_generator.generate.assert_called_once_with(requirement, improvement_hints=None)

    def test_finalize_generation_reports_aggregate_counts(self):
        state = make_state(test_cases=REQ_001_CASES + REQ_002_CASES)

        result = finalize_test_case_generation_node(state)

        assert result["current_step"] == "test_cases_generated"
        assert "2 requirements, 3 test cases" in result["agent_messages"][0]["content"]

    def test_generate_single_requirement_returns_bounded_login_only_case(self):
        requirement = {
            "id": "REQ_001",
            "title": "Restricted login verification",
            "scenario_type": "login_only",
            "generation_context": {
                "target_case_count": 1,
                "planning_mode": "bounded_login_only",
            },
        }

        result = generate_test_case_for_requirement_node(
            {
                "requirement": requirement,
                "strategy_context": requirement["generation_context"],
                "improvement_hints": None,
                "iteration_count": 0,
            }
        )

        assert len(result["test_cases"]) == 1
        assert result["test_cases"][0]["tags"] == ["smoke", "login", "login_only"]
        assert "bounded login-only" in result["agent_messages"][0]["content"]


class TestPlanningNode:
    def test_plan_case_budgets_node_consumes_strategy_and_adds_e2e(self):
        state = make_state(test_strategy=SAMPLE_STRATEGY_PLAN)

        result = plan_case_budgets_node(state)

        planned_requirements = result["requirements"]
        budgets = {
            requirement["id"]: requirement["generation_context"]["target_case_count"]
            for requirement in planned_requirements
        }

        assert len(planned_requirements) == 3
        assert planned_requirements[0]["flow_type"] == "setup"
        assert planned_requirements[1]["flow_type"] == "payment"
        assert planned_requirements[-1]["flow_type"] == "e2e"
        assert budgets["REQ_001"] == 1
        assert budgets["REQ_002"] >= 3

    def test_plan_case_budgets_node_skips_dynamic_planning_for_login_only_override(self):
        state = make_state(
            scenario_config={
                "scenario_type": "login_only",
                "page_url": "https://global.lianlianpay.com/signin",
                "success_signal": {"value": "LianLian"},
            }
        )

        result = plan_case_budgets_node(state)

        assert len(result["requirements"]) == 1
        requirement = result["requirements"][0]
        assert requirement["scenario_type"] == "login_only"
        assert requirement["generation_context"]["target_case_count"] == 1
        assert requirement["flow_type"] == "login_only"


class TestReviewNode:
    @patch("core.agents.workflow.nodes.review_nodes.CaseReviewer")
    def test_review_success(self, mock_reviewer_class):
        mock_reviewer = MagicMock()
        mock_reviewer.review_all.return_value = {
            "passed": True,
            "total_score": 92,
            "details": [
                {
                    "requirement_id": "REQ_001",
                    "comments": [{"type": "suggestion", "message": "Looks good"}],
                    "suggestions": ["Add a boundary test"],
                }
            ],
        }
        mock_reviewer_class.return_value = mock_reviewer

        result = review_test_cases_node(make_state(test_cases=REQ_001_CASES + REQ_002_CASES))

        assert result["review_passed"] is True
        assert result["review_score"] == 92
        assert result["review_comments"][0]["requirement_id"] == "REQ_001"
        assert result["review_suggestions"] == ["[REQ_001] Add a boundary test"]

    @patch("core.agents.workflow.nodes.review_nodes.CaseReviewer")
    def test_review_login_only_uses_deterministic_path(self, mock_reviewer_class):
        state = make_state(
            requirements=[
                {
                    "id": "REQ_001",
                    "title": "Restricted login verification",
                    "scenario_type": "login_only",
                }
            ],
            test_cases=[
                {
                    "id": "TC_001",
                    "requirement_id": "REQ_001",
                    "title": "Restricted login validation",
                    "steps": [{"step_number": 1, "action": "Open page", "expected": "Loaded"}],
                    "expected": "LianLian logo is visible",
                    "tags": ["smoke", "login", "login_only"],
                }
            ],
            scenario_config={
                "scenario_type": "login_only",
                "page_url": "https://global.lianlianpay.com/signin",
            },
        )

        result = review_test_cases_node(state)

        assert result["review_passed"] is True
        assert result["review_score"] == 100
        assert result["review_suggestions"] == []
        assert "Deterministic login-only review passed" in result["agent_messages"][0]["content"]
        mock_reviewer_class.assert_not_called()


class TestRoutingHelpers:
    def test_should_end_when_review_passes(self):
        assert should_regenerate(make_state(review_passed=True)) == "end"

    def test_should_regenerate_when_review_fails(self):
        assert should_regenerate(make_state(review_passed=False)) == "regenerate"

    def test_should_end_when_iteration_limit_is_reached(self):
        assert should_regenerate(make_state(review_passed=False, iteration_count=2)) == "end"

    def test_increment_iteration(self):
        result = increment_iteration(make_state(iteration_count=1))
        assert result["iteration_count"] == 2


class TestWorkflowIntegration:
    @patch("core.agents.workflow.nodes.script_nodes.MidsceneScriptGenerator")
    def test_plan_script_generation_node_stores_structured_plans(self, mock_generator_class):
        mock_generator = MagicMock()
        mock_plan = MagicMock()
        mock_plan.model_dump.return_value = {
            "testcase_id": "TC_001_001",
            "title": "Login succeeds with valid credentials",
            "scenario": {"scenario_type": "login", "execution_policy": "native_first"},
            "setup": {"page_url": "https://example.com/login"},
            "steps": [],
            "final_assertions": [],
            "fallback_policy": "deterministic",
            "metadata": {},
        }
        mock_generator.plan_script_generation.return_value = [mock_plan]
        mock_generator_class.return_value = mock_generator

        state = make_state(
            test_cases=REQ_001_CASES,
            test_strategy=SAMPLE_STRATEGY_PLAN,
        )

        result = plan_script_generation_node(state)

        assert result["current_step"] == "script_planned"
        assert len(result["script_plans"]) == 1
        mock_generator.plan_script_generation.assert_called_once_with(
            REQ_001_CASES,
            page_url="https://example.com/login",
            scenario_config=None,
            strategy_plan=SAMPLE_STRATEGY_PLAN,
        )

    def test_build_executor_env_overrides_maps_runtime_credentials(self):
        scenario_config = {
            "scenario_type": "login_only",
            "credentials": {
                "username_env": "LOGIN_USERNAME",
                "password_env": "LOGIN_PASSWORD",
                "username_value": "sample_user@example.com",
                "password_value": "sample-password-123",
            },
        }

        assert _build_executor_env_overrides(scenario_config) == {
            "LOGIN_USERNAME": "sample_user@example.com",
            "LOGIN_PASSWORD": "sample-password-123",
        }

    @patch("core.agents.workflow.nodes.script_nodes.os.path.exists", return_value=True)
    @patch("core.agents.workflow.nodes.script_nodes.MidsceneScriptGenerator")
    def test_generate_script_node_passes_login_only_scenario(self, mock_generator_class, _mock_exists):
        mock_generator = MagicMock()
        mock_generator.generate.return_value = os.path.join("midscene_run", "generated", "login-only.spec.ts")
        mock_generator_class.return_value = mock_generator

        scenario_config = {
            "scenario_type": "login_only",
            "page_url": "https://global.lianlianpay.com/signin",
            "success_signal": {"value": "LianLian"},
        }
        state = make_state(
            test_cases=REQ_001_CASES,
            page_url="https://global.lianlianpay.com/signin",
            scenario_config=scenario_config,
        )

        result = generate_script_node(state)

        assert result["generated_script"].endswith("login-only.spec.ts")
        mock_generator.generate.assert_called_once_with(
            REQ_001_CASES,
            page_url="https://global.lianlianpay.com/signin",
            scenario_config=scenario_config,
            strategy_plan=None,
            script_plans=None,
        )

    @patch("core.agents.workflow.nodes.execution_nodes.TestExecutor")
    def test_execute_tests_node_attaches_login_metadata(self, mock_executor_class):
        mock_executor = MagicMock()
        mock_executor.run_tests.return_value = {
            "status": "success",
            "total": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "duration": 2.5,
            "tests": [{"name": "TC_001", "status": "expected", "duration": 1000}],
        }
        mock_executor_class.return_value = mock_executor

        scenario_config = {
            "scenario_type": "login_only",
            "success_signal": {"value": "LianLian"},
            "mfa_mode": "manual_wait",
            "forbidden_actions": ["menu_click"],
        }
        state = make_state(
            generated_script=os.path.join("midscene_run", "generated", "login-only.spec.ts"),
            scenario_config=scenario_config,
        )

        result = execute_tests_node(state)

        assert result["execution_results"]["scenario_type"] == "login_only"
        assert result["execution_results"]["metadata"]["manual_wait"] is True
        assert result["execution_results"]["metadata"]["forbidden_actions"] == ["menu_click"]

    @patch("core.agents.workflow.nodes.execution_nodes.TestExecutor")
    def test_execute_tests_node_injects_requirement_credentials_into_executor_env(self, mock_executor_class):
        mock_executor = MagicMock()
        mock_executor.run_tests.return_value = {
            "status": "success",
            "total": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "duration": 2.5,
            "tests": [{"name": "TC_001", "status": "expected", "duration": 1000}],
        }
        mock_executor_class.return_value = mock_executor

        scenario_config = {
            "scenario_type": "login_only",
            "credentials": {
                "username_env": "LOGIN_USERNAME",
                "password_env": "LOGIN_PASSWORD",
                "username_value": "sample_user@example.com",
                "password_value": "sample-password-123",
            },
        }
        state = make_state(
            generated_script=os.path.join("midscene_run", "generated", "login-only.spec.ts"),
            scenario_config=scenario_config,
        )

        execute_tests_node(state)

        mock_executor_class.assert_called_once_with(
            config={
                "headed": True,
                "timeout": 180000,
                "env_overrides": {
                    "LOGIN_USERNAME": "sample_user@example.com",
                    "LOGIN_PASSWORD": "sample-password-123",
                },
            }
        )

    def test_build_workflow_contains_strategy_node(self):
        workflow = build_workflow()
        nodes = list(workflow.nodes.keys())

        assert "analyze_requirements" in nodes
        assert "plan_test_strategy" in nodes
        assert "plan_case_budgets" in nodes
        assert "plan_script_generation" in nodes
        assert "generate_test_case_for_requirement" in nodes

    @patch("core.agents.workflow.nodes.script_nodes.os.path.exists", return_value=True)
    @patch("core.agents.workflow.nodes.execution_nodes.AllureReporter")
    @patch("core.agents.workflow.nodes.execution_nodes.TestExecutor")
    @patch("core.agents.workflow.nodes.script_nodes.MidsceneScriptGenerator")
    @patch("core.agents.workflow.nodes.review_nodes.CaseReviewer")
    @patch("core.agents.workflow.nodes.generation_nodes.TestCaseGenerator")
    @patch("core.agents.workflow.nodes.planning_nodes.TestStrategyPlanner")
    @patch("core.agents.workflow.nodes.requirement_nodes.RequirementAnalyzer")
    def test_run_workflow_aggregates_strategy_driven_results(
        self,
        mock_analyzer_class,
        mock_strategy_class,
        mock_generator_class,
        mock_reviewer_class,
        mock_script_generator_class,
        mock_executor_class,
        mock_reporter_class,
        _mock_exists,
    ):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "requirements": SAMPLE_REQUIREMENTS,
            "summary": "Two requirements.",
        }
        mock_analyzer_class.return_value = mock_analyzer

        mock_strategy = MagicMock()
        mock_strategy.plan.return_value = SAMPLE_STRATEGY_PLAN
        mock_strategy_class.return_value = mock_strategy

        mock_generator = MagicMock()

        def generator_side_effect(requirement, improvement_hints=None):
            if requirement["id"] == "REQ_001":
                return REQ_001_CASES
            if requirement["id"] == "REQ_002":
                return REQ_002_CASES
            return [
                {
                    "id": "TC_003_001",
                    "requirement_id": requirement["id"],
                    "title": "E2E main path",
                    "steps": [
                        {
                            "step_number": 1,
                            "action": "Run the main path",
                            "expected": "The end-to-end flow completes",
                        }
                    ],
                    "expected": "The end-to-end flow completes",
                }
            ]

        mock_generator.generate.side_effect = generator_side_effect
        mock_generator_class.return_value = mock_generator

        mock_reviewer = MagicMock()
        mock_reviewer.review_all.return_value = {
            "passed": True,
            "total_score": 95,
            "details": [],
        }
        mock_reviewer_class.return_value = mock_reviewer

        mock_script_generator = MagicMock()
        mock_script_generator.generate.return_value = os.path.join("midscene_run", "generated", "parallel.spec.ts")
        mock_script_generator_class.return_value = mock_script_generator

        mock_executor = MagicMock()
        mock_executor.run_tests.return_value = {
            "status": "passed",
            "total": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 0,
            "duration": 1.2,
        }
        mock_executor_class.return_value = mock_executor

        mock_reporter = MagicMock()
        mock_reporter.check_allure_installed.return_value = True
        mock_reporter.generate_report.return_value = {
            "status": "success",
            "report_path": "allure-report",
        }
        mock_reporter_class.return_value = mock_reporter

        result = run_workflow(SAMPLE_REQUIREMENT_TEXT, max_iterations=2, page_url="https://example.com/login")

        assert len(result["requirements"]) == 3
        assert result["requirements"][-1]["flow_type"] == "e2e"
        assert len(result["test_cases"]) == 4
        assert result["review_passed"] is True
        assert result["execution_results"]["passed"] == 3
        assert result["allure_report_path"] == "allure-report"
        assert mock_generator.generate.call_count == 3

    @patch("core.agents.workflow.nodes.execution_nodes.Path")
    @patch("core.agents.workflow.nodes.execution_nodes.AllureReporter")
    def test_generate_report_node_materializes_results_from_execution(
        self,
        mock_reporter_class,
        mock_path_class,
    ):
        mock_reporter = MagicMock()
        mock_reporter.check_allure_installed.return_value = True
        mock_reporter.results_dir = "allure-results"
        mock_reporter.write_results_from_execution.return_value = {
            "created": 2,
            "passed": 1,
            "failed": 1,
            "broken": 0,
            "skipped": 0,
            "total": 2,
        }
        mock_reporter.generate_report.return_value = {
            "status": "success",
            "report_path": "allure-report",
        }
        mock_reporter_class.return_value = mock_reporter

        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = False
        mock_path_class.return_value = mock_results_dir

        state = make_state(
            generated_script=os.path.join("midscene_run", "generated", "demo.spec.ts"),
            execution_results={
                "tests": [
                    {"name": "TC_001", "status": "expected", "duration": 1200},
                    {"name": "TC_002", "status": "unexpected", "duration": 2400},
                ]
            },
        )

        result = generate_report_node(state)

        assert result["allure_report_path"] == "allure-report"
        mock_reporter.write_results_from_execution.assert_called_once_with(
            execution_results=state["execution_results"],
            script_path=state["generated_script"],
        )
