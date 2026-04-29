"""Fallback strategy builder for test strategy planning.

This module provides the FallbackStrategyBuilder class that handles
the construction of fallback strategies when LLM-based planning is unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from core.agents.strategy.focus_classifier import FocusPointClassifier
from core.agents.strategy.keywords import StrategyKeywords
from core.agents.strategy.utils import StrategyUtils
from core.models.requirement import Requirement
from core.models.test_strategy import (
    CoverageAxis,
    ExecutionMode,
    FocusLevel,
    FocusPointStrategy,
    OverallRisk,
    RequirementStrategy,
)

if TYPE_CHECKING:
    from core.models.config import StrategyConfig


class FallbackStrategyBuilder:
    """Builder for fallback test strategies.

    This class encapsulates all logic for building fallback strategies
    when LLM-based planning fails or is unavailable.
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize builder with optional configuration.

        Args:
            config: Strategy configuration for weights and thresholds
        """
        self.config = config
        self.classifier = FocusPointClassifier(config)

    def build_requirement_strategy(
        self,
        requirement: Requirement,
        *,
        multi_flow: bool,
    ) -> RequirementStrategy:
        """Build a fallback strategy for a single requirement.

        Args:
            requirement: The requirement to build strategy for
            multi_flow: Whether this is part of a multi-flow document

        Returns:
            RequirementStrategy with fallback focus points
        """
        source_points = requirement.acceptance_criteria or [requirement.description]
        focus_points = [
            self._build_focus_point(requirement, point_text, index=index, multi_flow=multi_flow)
            for index, point_text in enumerate(source_points, start=1)
        ]

        overall_risk = self._derive_overall_risk(focus_points)
        suggested_budget = self._calculate_case_budget(focus_points)
        summary = self._build_strategy_summary(requirement, focus_points, suggested_budget)

        return RequirementStrategy(
            requirement_id=requirement.id,
            focus_points=focus_points,
            overall_risk=overall_risk,
            suggested_case_budget=suggested_budget,
            strategy_summary=summary,
        )

    def build_from_dict(
        self,
        requirement_dict: dict,
        *,
        multi_flow: bool,
    ) -> RequirementStrategy:
        """Build a fallback strategy from a requirement dictionary.

        Args:
            requirement_dict: Dictionary containing requirement data
            multi_flow: Whether this is part of a multi-flow document

        Returns:
            RequirementStrategy with fallback focus points
        """
        requirement = Requirement.model_validate(requirement_dict)
        return self.build_requirement_strategy(requirement, multi_flow=multi_flow)

    def calculate_case_contribution(self, point: FocusPointStrategy) -> int:
        """Calculate the case contribution of a focus point.

        Args:
            point: The focus point to calculate contribution for

        Returns:
            Number of cases this focus point contributes
        """
        if point.focus_level == FocusLevel.CRITICAL:
            return 3 if point.execution_mode == ExecutionMode.DEEP else 2
        if point.focus_level == FocusLevel.MAJOR:
            return 2 if point.execution_mode == ExecutionMode.DEEP else 1
        if point.focus_level == FocusLevel.NORMAL:
            return 1
        return 0

    def _build_focus_point(
        self,
        requirement: Requirement,
        point_text: str,
        *,
        index: int,
        multi_flow: bool,
    ) -> FocusPointStrategy:
        """Build a single focus point.

        Args:
            requirement: The parent requirement
            point_text: The acceptance criterion text
            index: Index for point ID generation
            multi_flow: Whether this is part of a multi-flow document

        Returns:
            FocusPointStrategy instance
        """
        normalized_text = StrategyUtils.normalize(
            f"{requirement.title} {requirement.description} {point_text}"
        )

        coverage_axes = self.classifier.derive_coverage_axes(normalized_text)
        focus_level = self.classifier.classify_focus_level(
            requirement, normalized_text, coverage_axes, multi_flow=multi_flow
        )
        execution_mode = self.classifier.classify_execution_mode(focus_level, coverage_axes)
        reason = self._build_point_reason(requirement, normalized_text, focus_level, coverage_axes, multi_flow)

        return FocusPointStrategy(
            point_id=f"{requirement.id}_P{index:02d}",
            point_text=point_text.strip(),
            focus_level=focus_level,
            execution_mode=execution_mode,
            coverage_axes=coverage_axes,
            reason=reason,
            case_weight=self.classifier.focus_level_to_weight(focus_level),
        )

    def _derive_overall_risk(self, focus_points: List[FocusPointStrategy]) -> OverallRisk:
        """Derive overall risk level from focus points.

        Args:
            focus_points: List of focus points

        Returns:
            Highest risk level among all focus points
        """
        ranking = {
            FocusLevel.CRITICAL: OverallRisk.CRITICAL,
            FocusLevel.MAJOR: OverallRisk.HIGH,
            FocusLevel.NORMAL: OverallRisk.MEDIUM,
            FocusLevel.LIGHT: OverallRisk.LOW,
        }
        order = {
            OverallRisk.LOW: 1,
            OverallRisk.MEDIUM: 2,
            OverallRisk.HIGH: 3,
            OverallRisk.CRITICAL: 4,
        }

        best = OverallRisk.LOW
        for point in focus_points:
            candidate = ranking[point.focus_level]
            if order[candidate] > order[best]:
                best = candidate

        return best

    def _calculate_case_budget(self, focus_points: List[FocusPointStrategy]) -> int:
        """Calculate total case budget for focus points.

        Args:
            focus_points: List of focus points

        Returns:
            Total suggested case budget (capped at max_budget_per_requirement)
        """
        budget = sum(self.calculate_case_contribution(point) for point in focus_points)

        if self.config:
            max_budget = self.config.max_budget_per_requirement
        else:
            max_budget = 6

        return max(1, min(budget, max_budget))

    def _build_strategy_summary(
        self,
        requirement: Requirement,
        focus_points: List[FocusPointStrategy],
        suggested_budget: int,
    ) -> str:
        """Build a summary string for the strategy.

        Args:
            requirement: The parent requirement
            focus_points: List of focus points
            suggested_budget: Calculated budget

        Returns:
            Human-readable strategy summary
        """
        critical_count = sum(1 for item in focus_points if item.focus_level == FocusLevel.CRITICAL)
        major_count = sum(1 for item in focus_points if item.focus_level == FocusLevel.MAJOR)
        light_count = sum(1 for item in focus_points if item.focus_level == FocusLevel.LIGHT)

        return (
            f"{requirement.title} keeps budget {suggested_budget}; "
            f"{critical_count} critical, {major_count} major, {light_count} light points are expected."
        )

    def _build_point_reason(
        self,
        requirement: Requirement,
        normalized_text: str,
        focus_level: FocusLevel,
        coverage_axes: List[CoverageAxis],
        multi_flow: bool,
    ) -> str:
        """Build a reason string for a focus point classification.

        Args:
            requirement: The parent requirement
            normalized_text: Normalized text for keyword matching
            focus_level: Classified focus level
            coverage_axes: Derived coverage axes
            multi_flow: Whether this is part of a multi-flow document

        Returns:
            Human-readable reason for the classification
        """
        if focus_level == FocusLevel.CRITICAL:
            return "This point affects money, submission, status, security, or another high-risk outcome."

        if focus_level == FocusLevel.MAJOR:
            return "This point explicitly mentions failure handling, validation, exceptions, or recovery behavior."

        if focus_level == FocusLevel.LIGHT and multi_flow and StrategyUtils.is_login_related(normalized_text):
            return "Login acts as a prerequisite in a multi-flow document, so keep it merged into smoke coverage."

        if focus_level == FocusLevel.LIGHT:
            return "This point is mainly UI visibility, navigation, or low-risk presentation behavior."

        return f"Keep necessary coverage on {', '.join(axis.value for axis in coverage_axes)} without over-expanding cases."
