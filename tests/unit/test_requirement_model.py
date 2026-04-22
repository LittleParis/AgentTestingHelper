"""Requirement model unit tests - Issue #14 fix verification"""
import pytest
from pydantic import ValidationError

from core.models.requirement import Requirement, RequirementAnalysisResult, Priority, RequirementType


class TestRequirementIdPattern:
    """Test Requirement ID format - Issue #14 fix"""

    def test_valid_id_format_3_digits(self):
        """Test valid ID format with 3 digits"""
        req = Requirement(
            id="REQ_001",
            title="Login feature",
            description="User can login to the system",
            acceptance_criteria=["User enters valid credentials"]
        )
        assert req.id == "REQ_001"

    def test_valid_id_format_1_digit(self):
        """Test valid ID format with 1 digit (Issue #14: relaxed pattern)"""
        req = Requirement(
            id="REQ_1",
            title="Login feature",
            description="User can login to the system",
            acceptance_criteria=["User enters valid credentials"]
        )
        assert req.id == "REQ_1"

    def test_valid_id_format_6_digits(self):
        """Test valid ID format with 6 digits (Issue #14: support up to 6 digits)"""
        req = Requirement(
            id="REQ_123456",
            title="Login feature",
            description="User can login to the system",
            acceptance_criteria=["User enters valid credentials"]
        )
        assert req.id == "REQ_123456"

    def test_invalid_id_format_no_prefix(self):
        """Test invalid ID format without REQ_ prefix"""
        with pytest.raises(ValidationError):
            Requirement(
                id="001",  # Missing REQ_ prefix
                title="Login feature",
                description="User can login to the system",
                acceptance_criteria=["User enters valid credentials"]
            )

    def test_invalid_id_format_7_digits(self):
        """Test invalid ID format with 7 digits (exceeds limit)"""
        with pytest.raises(ValidationError):
            Requirement(
                id="REQ_1234567",  # 7 digits, exceeds 6 digit limit
                title="Login feature",
                description="User can login to the system",
                acceptance_criteria=["User enters valid credentials"]
            )
