"""Focus point classification logic for test strategy planning.

This module provides the FocusPointClassifier class that handles
the classification of focus_level, execution_mode, and coverage_axes
for individual acceptance points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from core.agents.strategy.keywords import StrategyKeywords
from core.agents.strategy.utils import StrategyUtils
from core.models.requirement import Requirement
from core.models.test_strategy import (
    CoverageAxis,
    ExecutionMode,
    FocusLevel,
)

if TYPE_CHECKING:
    from core.models.config import StrategyConfig


class FocusPointClassifier:
    """Classifier for focus point attributes.

    This class encapsulates all classification logic for determining
    focus_level, execution_mode, and coverage_axes based on keyword
    matching and context analysis.
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize classifier with optional configuration.

        Args:
            config: Strategy configuration for weights and thresholds
        """
        self.config = config

    def classify_focus_level(
        self,
        requirement: Requirement,
        normalized_text: str,
        coverage_axes: List[CoverageAxis],
        *,
        multi_flow: bool,
    ) -> FocusLevel:
        """Classify the focus level for a focus point.

        Args:
            requirement: The parent requirement
            normalized_text: Normalized text for keyword matching
            coverage_axes: Derived coverage axes
            multi_flow: Whether this is part of a multi-flow document

        Returns:
            Classified FocusLevel
        """
        # Critical keywords trigger critical level
        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.CRITICAL_KEYWORDS):
            return FocusLevel.CRITICAL

        # Major keywords trigger major level
        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.MAJOR_KEYWORDS):
            return FocusLevel.MAJOR

        # Light keywords trigger light level
        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.LIGHT_KEYWORDS):
            level = FocusLevel.LIGHT
        else:
            level = FocusLevel.NORMAL

        # Multi-flow login downgrade
        if multi_flow and StrategyUtils.is_login_related(normalized_text):
            if level in {FocusLevel.NORMAL, FocusLevel.LIGHT}:
                return FocusLevel.LIGHT

        # Multiple coverage dimensions upgrade
        if len(coverage_axes) >= 3 and level == FocusLevel.NORMAL:
            return FocusLevel.MAJOR

        return level

    def classify_execution_mode(
        self,
        focus_level: FocusLevel,
        coverage_axes: List[CoverageAxis],
    ) -> ExecutionMode:
        """Classify the execution mode for a focus point.

        Args:
            focus_level: The classified focus level
            coverage_axes: Derived coverage axes

        Returns:
            Classified ExecutionMode
        """
        if focus_level == FocusLevel.CRITICAL:
            return ExecutionMode.DEEP

        if focus_level == FocusLevel.MAJOR:
            return ExecutionMode.DEEP if len(coverage_axes) >= 2 else ExecutionMode.STANDARD

        if focus_level == FocusLevel.NORMAL:
            return ExecutionMode.STANDARD

        return ExecutionMode.SMOKE

    def derive_coverage_axes(self, normalized_text: str) -> List[CoverageAxis]:
        """Derive coverage axes from text content.

        Args:
            normalized_text: Normalized text for keyword matching

        Returns:
            List of applicable CoverageAxis values
        """
        axes: List[CoverageAxis] = [CoverageAxis.HAPPY_PATH]

        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.MAJOR_KEYWORDS):
            axes.append(CoverageAxis.NEGATIVE)

        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.BOUNDARY_KEYWORDS):
            axes.append(CoverageAxis.BOUNDARY)

        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.EXCEPTION_KEYWORDS):
            axes.append(CoverageAxis.EXCEPTION)

        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.RECOVERY_KEYWORDS):
            axes.append(CoverageAxis.RECOVERY)

        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.PERMISSION_KEYWORDS):
            axes.append(CoverageAxis.PERMISSION)

        if StrategyUtils.contains_any(normalized_text, StrategyKeywords.DATA_VALIDATION_KEYWORDS):
            axes.append(CoverageAxis.DATA_VALIDATION)

        # Deduplicate
        deduplicated: List[CoverageAxis] = []
        for axis in axes:
            if axis not in deduplicated:
                deduplicated.append(axis)

        return deduplicated

    def focus_level_to_weight(self, focus_level: FocusLevel) -> int:
        """Convert focus level to case weight.

        Args:
            focus_level: The focus level

        Returns:
            Case weight (1-3)
        """
        if self.config:
            weights = {
                FocusLevel.CRITICAL: self.config.critical_case_weight,
                FocusLevel.MAJOR: self.config.major_case_weight,
                FocusLevel.NORMAL: self.config.normal_case_weight,
                FocusLevel.LIGHT: 1,
            }
        else:
            weights = {
                FocusLevel.CRITICAL: 3,
                FocusLevel.MAJOR: 2,
                FocusLevel.NORMAL: 1,
                FocusLevel.LIGHT: 1,
            }

        return weights[focus_level]