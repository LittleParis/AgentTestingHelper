import os
from unittest.mock import MagicMock, patch

from langgraph.types import Overwrite, Send

from core.agents.workflow import (
    AgentState,
    analyze_requirements_node,
    build_workflow,
    execute_tests_node,
    fan_out_requirements,
    finalize_test_case_generation_node,
    generate_script_node,
    generate_report_node,
    generate_test_case_for_requirement_node,
    generate_test_cases_node,
    increment_iteration,
    review_test_cases_node,
    run_workflow,
    should_regenerate,
)


SAMPLE_REQUIREMENT_TEXT = """
# Login Feature

## Description
Users can log into the system with username and password.

## Acceptance Criteria
1. Valid credentials log in successfully.
2. Invalid password shows an error.
"""

SAMPLE_REQUIREMENTS = [
    {
        "id": "REQ_001",
        "title": "Successful login",
        "description": "Users can sign in with valid credentials.",
        "acceptance_criteria": [
            "A valid username and password should log in successfully.",
            "The system should redirect to the homepage after login.",
        ],
    },
    {
        "id": "REQ_002",
        "title": "Invalid password handling",
        "description": "The system should reject invalid passwords.",
        "acceptance_criteria": [
            "An invalid password should show an error message.",
            "The page should stay on the login form after failure.",
        ],
    },
]

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
        "title": "Login fails with invalid password",
        "steps": [
            {"step_number": 1, "action": "Open login page", "expected": "Login page is visible"},
            {"step_number": 2, "action": "Submit invalid password", "expected": "An error is shown"},
        ],
        "expected": "The system keeps the user on the login page.",
    }
]


def make_state(**overrides) -> AgentState:
    state: AgentState = {
        "requirement_text": SAMPLE_REQUIREMENT_TEXT,
        "requirements": SAMPLE_REQUIREMENTS,
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
    @patch("core.agents.workflow.RequirementAnalyzer")
    def test_analyze_success(self, mock_analyzer_class):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "requirements": SAMPLE_REQUIREMENTS,
            "summary": "Two login-related requirements.",
        }
        mock_analyzer_class.return_value = mock_analyzer

        result = analyze_requirements_node(make_state(requirements=None))

        assert result["requirements"] == SAMPLE_REQUIREMENTS
        assert result["requirement_summary"] == "Two login-related requirements."
        assert result["current_step"] == "requirement_analyzed"
        assert result["agent_messages"][0]["role"] == "analyzer"


class TestParallelGenerationNodes:
    def test_generate_dispatch_resets_state_for_parallel_run(self):
        result = generate_test_cases_node(make_state(test_cases=[{"id": "OLD_TC"}]))

        assert isinstance(result["test_cases"], Overwrite)
        assert result["test_cases"].value == []
        assert result["current_step"] == "test_case_generation_dispatched"
        assert "Dispatching" in result["agent_messages"][0]["content"]

    def test_fan_out_returns_one_send_per_requirement(self):
        sends = fan_out_requirements(make_state())

        assert len(sends) == 2
        assert all(isinstance(item, Send) for item in sends)
        assert sends[0].node == "generate_test_case_for_requirement"
        assert sends[0].arg["requirement"]["id"] == "REQ_001"
        assert sends[1].arg["requirement"]["id"] == "REQ_002"

    @patch("core.agents.workflow.TestCaseGenerator")
    def test_generate_single_requirement_returns_partial_cases(self, mock_generator_class):
        mock_generator = MagicMock()
        mock_generator.generate.return_value = REQ_001_CASES
        mock_generator_class.return_value = mock_generator

        result = generate_test_case_for_requirement_node(
            {
                "requirement": SAMPLE_REQUIREMENTS[0],
                "improvement_hints": None,
                "iteration_count": 0,
            }
        )

        assert result["test_cases"] == REQ_001_CASES
        assert "REQ_001" in result["agent_messages"][0]["content"]
        mock_generator.generate.assert_called_once_with(SAMPLE_REQUIREMENTS[0], improvement_hints=None)

    def test_finalize_generation_reports_aggregate_counts(self):
        state = make_state(test_cases=REQ_001_CASES + REQ_002_CASES)

        result = finalize_test_case_generation_node(state)

        assert result["current_step"] == "test_cases_generated"
        assert "2 requirements, 2 test cases" in result["agent_messages"][0]["content"]


class TestReviewNode:
    @patch("core.agents.workflow.CaseReviewer")
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
    @patch("core.agents.workflow.os.path.exists", return_value=True)
    @patch("core.agents.workflow.MidsceneScriptGenerator")
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
        )

    @patch("core.agents.workflow.TestExecutor")
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

    def test_build_workflow_contains_parallel_generation_nodes(self):
        workflow = build_workflow()
        nodes = list(workflow.nodes.keys())

        assert "analyze_requirements" in nodes
        assert "generate_test_cases" in nodes
        assert "generate_test_case_for_requirement" in nodes
        assert "finalize_test_case_generation" in nodes
        assert "review_test_cases" in nodes

    @patch("core.agents.workflow.os.path.exists", return_value=True)
    @patch("core.agents.workflow.AllureReporter")
    @patch("core.agents.workflow.TestExecutor")
    @patch("core.agents.workflow.MidsceneScriptGenerator")
    @patch("core.agents.workflow.CaseReviewer")
    @patch("core.agents.workflow.TestCaseGenerator")
    @patch("core.agents.workflow.RequirementAnalyzer")
    def test_run_workflow_aggregates_parallel_results(
        self,
        mock_analyzer_class,
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
            "summary": "Two login-related requirements.",
        }
        mock_analyzer_class.return_value = mock_analyzer

        mock_generator = MagicMock()

        def generator_side_effect(requirement, improvement_hints=None):
            if requirement["id"] == "REQ_001":
                return REQ_001_CASES
            if requirement["id"] == "REQ_002":
                return REQ_002_CASES
            return []

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
            "total": 2,
            "passed": 2,
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

        assert result["requirements"] == SAMPLE_REQUIREMENTS
        assert len(result["test_cases"]) == 2
        assert result["review_passed"] is True
        assert result["execution_results"]["passed"] == 2
        assert result["allure_report_path"] == "allure-report"
        assert mock_generator.generate.call_count == 2

    @patch("core.agents.workflow.Path")
    @patch("core.agents.workflow.AllureReporter")
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
