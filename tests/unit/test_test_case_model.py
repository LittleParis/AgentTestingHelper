"""TestCase model unit tests - Issue #15 fix verification"""
import pytest
from pydantic import ValidationError

from core.models.test_case import TestCase, TestStep, TestCaseType
from core.models.requirement import Priority


class TestTestStep:
    """Test TestStep model"""

    def test_valid_test_step(self):
        """Test valid test step"""
        step = TestStep(
            step_number=1,
            action="Click login button",
            expected="Navigate to homepage"
        )
        assert step.step_number == 1
        assert step.action == "Click login button"

    def test_test_step_with_data(self):
        """Test test step with data"""
        step = TestStep(
            step_number=1,
            action="Enter username",
            data="test@example.com",
            expected="Input shows email"
        )
        assert step.data == "test@example.com"


class TestTestCaseTitleValidation:
    """Test TestCase title validation - Issue #15 fix"""

    def test_title_starts_with_digit_allowed(self):
        """Title starting with digit is now allowed"""
        tc = TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="1. Verify user login success",
            steps=[
                TestStep(step_number=1, action="Enter username", expected="Display username")
            ],
            expected="Login successful"
        )
        assert tc.title == "1. Verify user login success"

    def test_title_with_tc_prefix_allowed(self):
        """Title with TC prefix number is allowed"""
        tc = TestCase(
            id="TC_002",
            requirement_id="REQ_001",
            title="TC001 Normal login flow",
            steps=[
                TestStep(step_number=1, action="Click login button", expected="Navigate to homepage")
            ],
            expected="Login successful"
        )
        assert tc.title == "TC001 Normal login flow"

    def test_title_with_newline_rejected(self):
        """Title with newline is rejected"""
        with pytest.raises(ValidationError):
            TestCase(
                id="TC_001",
                requirement_id="REQ_001",
                title="Test\ntitle",
                steps=[
                    TestStep(step_number=1, action="Execute operation", expected="Operation result")
                ],
                expected="Expected result"
            )

    def test_title_with_special_chars_rejected(self):
        """Title with special characters is rejected"""
        with pytest.raises(ValidationError):
            TestCase(
                id="TC_001",
                requirement_id="REQ_001",
                title="Test<title>",
                steps=[
                    TestStep(step_number=1, action="Execute operation", expected="Operation result")
                ],
                expected="Expected result"
            )

    def test_title_trimmed(self):
        """Title is automatically trimmed"""
        tc = TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="  Test Title  ",
            steps=[
                TestStep(step_number=1, action="Execute operation", expected="Operation result")
            ],
            expected="Expected result"
        )
        assert tc.title == "Test Title"


class TestTestCaseIdPattern:
    """Test TestCase ID format - Issue #14 fix"""

    def test_valid_id_format_3_digits(self):
        """Test valid ID format with 3 digits"""
        tc = TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="Test case title",
            steps=[
                TestStep(step_number=1, action="Execute operation", expected="Operation result")
            ],
            expected="Expected result"
        )
        assert tc.id == "TC_001"

    def test_valid_id_format_4_digits(self):
        """Test valid ID format with 4 digits (Issue #14: relaxed pattern)"""
        tc = TestCase(
            id="TC_0001",
            requirement_id="REQ_001",
            title="Test case title",
            steps=[
                TestStep(step_number=1, action="Execute operation", expected="Operation result")
            ],
            expected="Expected result"
        )
        assert tc.id == "TC_0001"

    def test_valid_id_format_sub_case(self):
        """Test valid ID format with sub-case notation (Issue #14: TC_001_001)"""
        tc = TestCase(
            id="TC_001_001",
            requirement_id="REQ_001",
            title="Test case title",
            steps=[
                TestStep(step_number=1, action="Execute operation", expected="Operation result")
            ],
            expected="Expected result"
        )
        assert tc.id == "TC_001_001"

    def test_invalid_id_format_no_prefix(self):
        """Test invalid ID format without TC_ prefix"""
        with pytest.raises(ValidationError):
            TestCase(
                id="001",  # Missing TC_ prefix
                requirement_id="REQ_001",
                title="Test case title",
                steps=[
                    TestStep(step_number=1, action="Execute operation", expected="Operation result")
                ],
                expected="Expected result"
            )


class TestTestCaseStepsValidation:
    """Test step sequence validation"""

    def test_steps_sequence_valid(self):
        """Test step sequence is valid"""
        tc = TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="Test case title",
            steps=[
                TestStep(step_number=1, action="Execute step one", expected="Result one"),
                TestStep(step_number=2, action="Execute step two", expected="Result two"),
                TestStep(step_number=3, action="Execute step three", expected="Result three")
            ],
            expected="Final result"
        )
        assert tc.get_step_count() == 3

    def test_steps_sequence_invalid(self):
        """Test step sequence is invalid"""
        with pytest.raises(ValidationError):
            TestCase(
                id="TC_001",
                requirement_id="REQ_001",
                title="Test case title",
                steps=[
                    TestStep(step_number=1, action="Execute step one", expected="Result one"),
                    TestStep(step_number=3, action="Execute step three", expected="Result three")  # Skip 2
                ],
                expected="Final result"
            )


class TestTestCaseDefaults:
    """Test default values"""

    def test_default_priority(self):
        """Test default priority"""
        tc = TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="Test case title",
            steps=[
                TestStep(step_number=1, action="Execute operation", expected="Operation result")
            ],
            expected="Expected result"
        )
        assert tc.priority == Priority.MEDIUM

    def test_default_type(self):
        """Test default type"""
        tc = TestCase(
            id="TC_001",
            requirement_id="REQ_001",
            title="Test case title",
            steps=[
                TestStep(step_number=1, action="Execute operation", expected="Operation result")
            ],
            expected="Expected result"
        )
        assert tc.type == TestCaseType.FUNCTIONAL
