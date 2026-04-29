"""Normalize strategy output into requirement-level case budgets.

This module provides the CaseBudgetPlanner class that transforms
test strategies into runtime-friendly generation budgets.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from core.agents.strategy.keywords import StrategyKeywords
from core.agents.strategy.utils import StrategyUtils
from core.agents.test_strategy_planner import TestStrategyPlanner
from core.models.config import get_settings
from core.models.requirement import Priority, Requirement, RequirementType
from core.models.test_strategy import (
    CoverageAxis,
    ExecutionMode,
    FocusLevel,
    FocusPointStrategy,
    OverallRisk,
    RequirementStrategy,
    TestStrategyPlan,
)


class CaseBudgetPlanner:
    """Turn strategy output into compact, runtime-friendly generation budgets.

    This class consumes test strategies and produces requirement dictionaries
    enriched with generation_context for test case generation.
    """

    def __init__(self, config: Optional["StrategyConfig"] = None):
        """Initialize planner with optional configuration.

        Args:
            config: Strategy configuration for weights and thresholds
        """
        self.config = config or get_settings().get_strategy_config()
        self._strategy_planner: Optional[TestStrategyPlanner] = None

    def plan(
        self,
        requirement_text: str,
        analyzed_requirements: Optional[List[Dict[str, Any]]] = None,
        strategy_plan: Optional[Dict[str, Any] | TestStrategyPlan] = None,
        page_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return planned requirements enriched with generation context.

        Args:
            requirement_text: Raw requirement document text
            analyzed_requirements: List of analyzed requirements
            strategy_plan: Optional pre-computed strategy plan
            page_url: Optional page URL for the requirements

        Returns:
            List of requirement dictionaries with generation_context
        """
        requirements = [self._ensure_requirement_dict(item) for item in (analyzed_requirements or [])]
        if not requirements:
            return []

        # Parse or generate strategy plan
        parsed_strategy = self._parse_strategy_plan(strategy_plan)
        if parsed_strategy is None or not parsed_strategy.requirement_strategies:
            if self._strategy_planner is None:
                self._strategy_planner = TestStrategyPlanner(self.config)
            parsed_strategy = self._strategy_planner.plan_structured(
                requirement_text,
                [Requirement.model_validate(r) for r in requirements],
            )

        planned = self._plan_from_strategy(requirements, parsed_strategy, page_url=page_url)

        # Add E2E requirement for multi-flow documents
        if len(requirements) > 1:
            planned.append(self._build_e2e_requirement(requirements, page_url=page_url))

        self._cap_total_case_budget(planned)
        return planned

    def _plan_from_strategy(
        self,
        requirements: List[Dict[str, Any]],
        strategy_plan: TestStrategyPlan,
        *,
        page_url: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Build planned requirements from strategy.

        Args:
            requirements: List of requirement dictionaries
            strategy_plan: Test strategy plan
            page_url: Optional page URL

        Returns:
            List of planned requirements with generation_context
        """
        planned: List[Dict[str, Any]] = []

        for requirement in requirements:
            requirement_strategy = strategy_plan.get_strategy_for_requirement(requirement["id"])
            if requirement_strategy is None:
                # Should not happen if strategy_plan is complete
                continue

            planned.append(
                self._decorate_requirement(
                    requirement=requirement,
                    generation_context=self._build_generation_context(
                        requirement=requirement,
                        strategy=requirement_strategy,
                    ),
                    page_url=page_url,
                )
            )

        return planned

    def _decorate_requirement(
        self,
        *,
        requirement: Dict[str, Any],
        generation_context: Dict[str, Any],
        page_url: Optional[str],
    ) -> Dict[str, Any]:
        """Decorate requirement with flow metadata and generation context.

        Args:
            requirement: Base requirement dictionary
            generation_context: Generation context to add
            page_url: Optional page URL

        Returns:
            Decorated requirement dictionary
        """
        payload = dict(requirement)
        payload.setdefault("type", "functional")
        flow_type = self._classify_flow_type(payload)
        payload["flow_name"] = payload.get("title") or payload["id"]
        payload["flow_type"] = flow_type
        if page_url and not payload.get("page_url"):
            payload["page_url"] = page_url
        payload["generation_context"] = generation_context
        return payload

    def _build_generation_context(
        self,
        *,
        requirement: Dict[str, Any],
        strategy: RequirementStrategy,
    ) -> Dict[str, Any]:
        """Build simplified generation context.

        This method produces a minimal context with only the fields
        actually used by TestCaseGenerator.

        Args:
            requirement: Requirement dictionary
            strategy: Requirement strategy

        Returns:
            Simplified generation context dictionary
        """
        # Calculate target case count
        budget = sum(
            self._focus_point_case_contribution(point)
            for point in strategy.focus_points
        )
        max_budget = self.config.max_budget_per_requirement
        target_case_count = max(1, min(max(budget, strategy.suggested_case_budget), max_budget))

        # Extract focus points
        focus_points = [point.model_dump(mode="json") for point in strategy.focus_points]

        # Collect coverage axes
        coverage_focus = self._collect_coverage_axes(strategy.focus_points)

        return {
            "target_case_count": target_case_count,
            "case_id_prefix": str(requirement["id"]).split("_", 1)[-1],
            "focus_points": focus_points,
            "coverage_focus": coverage_focus,
            "overall_risk": strategy.overall_risk.value,
        }

    def _focus_point_case_contribution(self, point: FocusPointStrategy) -> int:
        """Calculate case contribution for a focus point.

        Args:
            point: Focus point strategy

        Returns:
            Number of cases this point contributes
        """
        if point.focus_level == FocusLevel.CRITICAL:
            return 3 if point.execution_mode == ExecutionMode.DEEP else 2
        if point.focus_level == FocusLevel.MAJOR:
            return 2 if point.execution_mode == ExecutionMode.DEEP else 1
        if point.focus_level == FocusLevel.NORMAL:
            return 1
        return 0

    def _collect_coverage_axes(self, focus_points: List[FocusPointStrategy]) -> List[str]:
        """Collect unique coverage axes from focus points.

        Args:
            focus_points: List of focus point strategies

        Returns:
            List of unique coverage axis values
        """
        ordered: List[str] = []
        for point in focus_points:
            for axis in point.coverage_axes:
                axis_value = axis.value
                if axis_value not in ordered:
                    ordered.append(axis_value)
        return ordered or [CoverageAxis.HAPPY_PATH.value]

    def _build_e2e_requirement(
        self,
        requirements: List[Dict[str, Any]],
        *,
        page_url: Optional[str],
    ) -> Dict[str, Any]:
        """Build an E2E requirement for multi-flow documents.

        Args:
            requirements: List of existing requirements
            page_url: Optional page URL

        Returns:
            E2E requirement dictionary
        """
        next_requirement_id = self._next_requirement_id(requirements)
        titles = [item.get("title") or item["id"] for item in requirements]
        happy_path_text = " -> ".join(titles)

        focus_point = FocusPointStrategy(
            point_id=f"{next_requirement_id}_P01",
            point_text=f"Complete the primary end-to-end path across {happy_path_text}.",
            focus_level=FocusLevel.MAJOR,
            execution_mode=ExecutionMode.SMOKE,
            coverage_axes=[CoverageAxis.HAPPY_PATH],
            reason="Reserve one document-level main-path case across multiple requirements.",
            case_weight=1,
        )

        generation_context = {
            "target_case_count": 1,
            "case_id_prefix": str(next_requirement_id).split("_", 1)[-1],
            "focus_points": [focus_point.model_dump(mode="json")],
            "coverage_focus": [CoverageAxis.HAPPY_PATH.value],
            "overall_risk": OverallRisk.HIGH.value,
        }

        description = f"Verify the primary business path across {happy_path_text}."
        if page_url:
            description += f" Start from {page_url}."

        return {
            "id": next_requirement_id,
            "title": "End-to-end main path validation",
            "description": description,
            "priority": "high",
            "type": "functional",
            "acceptance_criteria": [focus_point.point_text],
            "ui_elements": [],
            "flow_name": "End-to-end main path",
            "flow_type": "e2e",
            "page_url": page_url,
            "generation_context": generation_context,
        }

    def _cap_total_case_budget(self, planned_requirements: List[Dict[str, Any]]) -> None:
        """Cap total case budget to max_total_cases.

        Args:
            planned_requirements: List of planned requirements (modified in place)
        """
        max_total = self.config.max_total_cases

        while self._sum_case_budget(planned_requirements) > max_total:
            candidate = self._pick_budget_reduction_candidate(planned_requirements)
            if candidate is None:
                break

            context = candidate.get("generation_context") or {}
            context["target_case_count"] = int(context.get("target_case_count") or 1) - 1
            context["budget_reduced"] = True
            candidate["generation_context"] = context

    def _pick_budget_reduction_candidate(
        self,
        planned_requirements: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Pick the best candidate for budget reduction.

        Args:
            planned_requirements: List of planned requirements

        Returns:
            Best candidate for reduction, or None if no reduction possible
        """
        best_candidate: Optional[Dict[str, Any]] = None
        best_score = -1

        for requirement in planned_requirements:
            context = requirement.get("generation_context") or {}
            current = int(context.get("target_case_count") or 0)
            minimum = self._minimum_budget(context)
            if current <= minimum:
                continue

            score = self._budget_reduction_score(context)
            if score > best_score:
                best_score = score
                best_candidate = requirement

        return best_candidate

    def _budget_reduction_score(self, context: Dict[str, Any]) -> int:
        """Calculate budget reduction score for a requirement.

        Higher score = more suitable for reduction.

        Args:
            context: Generation context

        Returns:
            Reduction score
        """
        if context.get("flow_type") == "e2e":
            return -1

        # Count focus points by level
        focus_points = context.get("focus_points") or []
        light = sum(1 for p in focus_points if p.get("focus_level") == "light")
        normal = sum(1 for p in focus_points if p.get("focus_level") == "normal")
        major = sum(1 for p in focus_points if p.get("focus_level") == "major")
        critical = sum(1 for p in focus_points if p.get("focus_level") == "critical")

        risk_penalty = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }.get(str(context.get("overall_risk") or "medium"), 2)

        return light * 10 + normal * 6 + risk_penalty * 2 - major * 2 - critical * 4

    def _minimum_budget(self, context: Dict[str, Any]) -> int:
        """Calculate minimum budget for a requirement.

        Args:
            context: Generation context

        Returns:
            Minimum allowed budget
        """
        if context.get("flow_type") == "e2e":
            return 1

        focus_points = context.get("focus_points") or []
        has_critical = any(p.get("focus_level") == "critical" for p in focus_points)
        has_major = any(p.get("focus_level") == "major" for p in focus_points)

        if has_critical:
            return 2
        if has_major:
            return 1
        return 1

    def _sum_case_budget(self, planned_requirements: List[Dict[str, Any]]) -> int:
        """Sum total case budget.

        Args:
            planned_requirements: List of planned requirements

        Returns:
            Total case budget
        """
        return sum(
            int((requirement.get("generation_context") or {}).get("target_case_count") or 0)
            for requirement in planned_requirements
        )

    def _parse_strategy_plan(
        self,
        strategy_plan: Optional[Dict[str, Any] | TestStrategyPlan],
    ) -> Optional[TestStrategyPlan]:
        """Parse strategy plan from dict or TestStrategyPlan.

        Args:
            strategy_plan: Strategy plan input

        Returns:
            TestStrategyPlan instance or None
        """
        if strategy_plan is None:
            return None
        if isinstance(strategy_plan, TestStrategyPlan):
            return strategy_plan
        try:
            return TestStrategyPlan.model_validate(strategy_plan)
        except Exception:
            return None

    def _ensure_requirement_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure item is a valid requirement dictionary.

        Args:
            item: Input dictionary

        Returns:
            Valid requirement dictionary
        """
        try:
            requirement = Requirement.model_validate(item)
        except Exception:
            payload = dict(item or {})
            description = str(payload.get("description") or "").strip()
            if len(description) < 10:
                description = f"{description} Core flow validation.".strip()
            priority_value = str(payload.get("priority") or "medium")
            type_value = str(payload.get("type") or "functional")
            requirement = Requirement(
                id=str(payload.get("id") or "REQ_001"),
                title=str(payload.get("title") or "Untitled requirement"),
                description=description,
                priority=Priority(priority_value if priority_value in {"high", "medium", "low"} else "medium"),
                type=RequirementType(
                    type_value
                    if type_value in {"functional", "non_functional", "business", "technical"}
                    else "functional"
                ),
                acceptance_criteria=payload.get("acceptance_criteria") or ["Core flow works correctly."],
                ui_elements=payload.get("ui_elements") or [],
            )
        return requirement.model_dump(mode="json")

    def _next_requirement_id(self, requirements: Iterable[Dict[str, Any]]) -> str:
        """Generate next requirement ID.

        Args:
            requirements: Existing requirements

        Returns:
            Next available requirement ID
        """
        highest = 0
        for requirement in requirements:
            raw_id = str(requirement.get("id") or "")
            if raw_id.startswith("REQ_"):
                suffix = raw_id.split("_", 1)[-1]
                if suffix.isdigit():
                    highest = max(highest, int(suffix))
        return f"REQ_{highest + 1:03d}"

    def _classify_flow_type(self, requirement: Dict[str, Any]) -> str:
        """Classify the flow type of a requirement.

        Args:
            requirement: Requirement dictionary

        Returns:
            Flow type string
        """
        text = StrategyUtils.normalize(
            " ".join(
                [
                    str(requirement.get("title") or ""),
                    str(requirement.get("description") or ""),
                    " ".join(str(item) for item in (requirement.get("acceptance_criteria") or [])),
                ]
            )
        )
        if StrategyUtils.is_payment_related(text):
            return "payment"
        if StrategyUtils.is_order_related(text):
            return "core_business"
        if StrategyUtils.is_login_related(text):
            return "setup"
        return "requirement"
