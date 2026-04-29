"""LLM-backed review agent for generated test cases."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Union

from pydantic import ValidationError

from core.models.requirement import Requirement
from core.models.review import (
    CommentSeverity,
    CommentType,
    RequirementReviewDetail,
    ReviewAllResult,
    ReviewComment,
    ReviewDimensions,
    ReviewResult,
)
from core.models.test_case import TestCase, TestCaseType, TestStep
from core.models.requirement import Priority
from core.utils.llm_client import get_llm_client


class CaseReviewer:
    """Review generated test cases with structured output and heuristics."""

    def __init__(self):
        self.llm = get_llm_client()

    def review(
        self,
        requirement: Union[Dict[str, Any], Requirement],
        test_cases: Union[List[Dict[str, Any]], List[TestCase]],
    ) -> Dict[str, Any]:
        return self.review_structured(
            self._to_requirement(requirement),
            self._to_test_cases(test_cases),
        ).to_dict()

    def review_structured(self, requirement: Requirement, test_cases: List[TestCase]) -> ReviewResult:
        prompt = self._build_review_prompt(requirement, test_cases)
        try:
            result = self.llm.invoke_structured(
                ReviewResult,
                prompt,
                operation=f"case_review_{requirement.id}",
            )
            if isinstance(result, ReviewResult):
                return self._normalize_executability(result)
            return self._build_review_result(result)
        except ValidationError as exc:
            print(f"[Reviewer] validation failed: {exc}")
            return self._fallback_invoke(prompt)
        except Exception as exc:
            print(f"[Reviewer] structured output failed: {exc}")
            return self._fallback_invoke(prompt)

    def _fallback_invoke(self, prompt: str) -> ReviewResult:
        print("[Reviewer] using fallback parser")
        try:
            response = self.llm.chat_simple(prompt)
            return self._parse_response(response)
        except Exception as exc:
            print(f"[Reviewer] fallback parser failed: {exc}")
            return self._fallback_review_result()

    def review_all(
        self,
        requirements: List[Union[Dict[str, Any], Requirement]],
        all_test_cases: List[Union[Dict[str, Any], TestCase]],
    ) -> Dict[str, Any]:
        reqs = [self._to_requirement(req) for req in requirements]
        cases = [self._to_test_case(case) if isinstance(case, dict) else case for case in all_test_cases]
        return self.review_all_structured(reqs, cases).to_dict()

    def review_all_structured(
        self,
        requirements: List[Requirement],
        all_test_cases: List[TestCase],
    ) -> ReviewAllResult:
        grouped_cases = self._group_cases_by_requirement(all_test_cases)
        details: List[RequirementReviewDetail] = []
        total_score = 0

        for requirement in requirements:
            req_cases = grouped_cases.get(requirement.id, [])
            if not req_cases:
                details.append(
                    RequirementReviewDetail(
                        requirement_id=requirement.id,
                        requirement_title=requirement.title,
                        passed=False,
                        score=0,
                        comments=[
                            ReviewComment(
                                type=CommentType.NO_COVERAGE,
                                severity=CommentSeverity.HIGH,
                                message=f"Requirement {requirement.id} has no generated test cases.",
                            )
                        ],
                        suggestions=["Generate at least one executable case for this requirement."],
                        executability_score=0,
                        executability_findings=["No executable case exists for this requirement."],
                    )
                )
                continue

            result = self.review_structured(requirement, req_cases)
            details.append(
                RequirementReviewDetail(
                    requirement_id=requirement.id,
                    requirement_title=requirement.title,
                    passed=result.passed,
                    score=result.score,
                    dimensions=result.dimensions,
                    comments=result.comments,
                    suggestions=result.suggestions,
                    executability_score=result.executability_score,
                    executability_findings=result.executability_findings,
                )
            )
            total_score += result.score

        average_score = total_score / len(requirements) if requirements else 0
        passed = all(detail.passed for detail in details) and average_score >= 60
        summary = self._generate_summary(details)
        return ReviewAllResult(
            passed=passed,
            total_score=round(average_score, 1),
            details=details,
            summary=summary,
        )

    def _to_requirement(self, req: Union[Dict[str, Any], Requirement]) -> Requirement:
        if isinstance(req, Requirement):
            return req
        try:
            return Requirement.model_validate(req)
        except ValidationError:
            return Requirement(
                id=req.get("id", "REQ_001"),
                title=req.get("title", "Untitled requirement"),
                description=req.get("description", "Requirement description"),
                acceptance_criteria=req.get("acceptance_criteria", ["Core behavior works as expected"]),
            )

    def _to_test_case(self, case: Union[Dict[str, Any], TestCase]) -> TestCase:
        if isinstance(case, TestCase):
            return case
        try:
            return TestCase.model_validate(case)
        except ValidationError:
            return TestCase(
                id=case.get("id", "TC_001"),
                requirement_id=case.get("requirement_id", "REQ_001"),
                title=case.get("title", "Generated test case"),
                type=TestCaseType.FUNCTIONAL,
                priority=Priority.MEDIUM,
                steps=[TestStep(step_number=1, action="Execute test step", expected="Expected result is visible")],
                expected=case.get("expected", "Expected result is visible"),
            )

    def _to_test_cases(self, cases: Union[List[Dict[str, Any]], List[TestCase]]) -> List[TestCase]:
        return [self._to_test_case(case) for case in cases]

    def _build_review_prompt(self, requirement: Requirement, test_cases: List[TestCase]) -> str:
        requirement_json = requirement.model_dump_json(indent=2)
        cases_json = json.dumps([case.model_dump(mode="json") for case in test_cases], ensure_ascii=False, indent=2)
        return f"""You are a senior test design reviewer.

Review the generated test cases against the requirement.

Requirement:
{requirement_json}

Generated test cases:
{cases_json}

Score these five dimensions from 0 to 20:
1. completeness
2. coverage
3. reasonability
4. independence
5. clarity

Also provide an executability_score from 0 to 20 that is NOT included in score.
Executability should focus on:
- missing explicit targets in steps
- vague expected results
- hidden prerequisites or test chaining
- steps that are hard to map to deterministic UI actions

Return JSON only:
{{
  "score": 80,
  "passed": true,
  "dimensions": {{
    "completeness": 16,
    "coverage": 16,
    "reasonability": 16,
    "independence": 16,
    "clarity": 16
  }},
  "comments": [
    {{
      "type": "suggestion",
      "severity": "medium",
      "message": "Add a boundary case for an empty password."
    }}
  ],
  "suggestions": [
    "Add one negative case for empty password."
  ],
  "executability_score": 15,
  "executability_findings": [
    "Expected result wording is vague in two steps."
  ]
}}
"""

    def _parse_response(self, response: str) -> ReviewResult:
        content = response.strip()
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            return self._build_review_result(json.loads(content))
        except json.JSONDecodeError:
            return ReviewResult(
                passed=False,
                score=0,
                comments=[
                    ReviewComment(
                        type=CommentType.PARSE_ERROR,
                        severity=CommentSeverity.HIGH,
                        message="Failed to parse the reviewer response as JSON.",
                    )
                ],
                suggestions=["Inspect the reviewer prompt or fallback parser."],
                executability_score=0,
                executability_findings=["Structured reviewer output could not be parsed."],
            )

    def _build_review_result(self, data: Dict[str, Any]) -> ReviewResult:
        try:
            dimensions = None
            if "dimensions" in data:
                dimensions = ReviewDimensions(
                    completeness=data["dimensions"].get("completeness", 10),
                    coverage=data["dimensions"].get("coverage", 10),
                    reasonability=data["dimensions"].get("reasonability", 10),
                    independence=data["dimensions"].get("independence", 10),
                    clarity=data["dimensions"].get("clarity", 10),
                )

            comments: List[ReviewComment] = []
            for raw_comment in data.get("comments", []):
                try:
                    comments.append(
                        ReviewComment(
                            type=CommentType(raw_comment.get("type", "suggestion")),
                            severity=CommentSeverity(raw_comment.get("severity", "medium")),
                            message=raw_comment.get("message", ""),
                            field=raw_comment.get("field"),
                        )
                    )
                except ValueError:
                    comments.append(
                        ReviewComment(
                            type=CommentType.SUGGESTION,
                            severity=CommentSeverity.MEDIUM,
                            message=raw_comment.get("message", "General review suggestion."),
                        )
                    )

            score = data.get("score", 0)
            if dimensions:
                score = dimensions.total()

            result = ReviewResult(
                passed=data.get("passed", score >= 60),
                score=score,
                dimensions=dimensions,
                comments=comments,
                suggestions=data.get("suggestions", []),
                executability_score=data.get("executability_score"),
                executability_findings=data.get("executability_findings", []),
            )
            return self._normalize_executability(result)
        except ValidationError:
            return self._fallback_review_result()

    def _normalize_executability(self, result: ReviewResult) -> ReviewResult:
        if result.executability_score is not None and result.executability_findings:
            return result

        score = 20 if result.executability_score is None else result.executability_score
        findings = list(result.executability_findings)
        for comment in result.comments:
            lowered = comment.message.lower()
            if any(token in lowered for token in ["vague", "模糊", "normal", "successfully", "正常", "成功"]):
                score -= 3
                findings.append("Expected result wording is too vague for deterministic execution.")
            if any(token in lowered for token in ["dependency", "前置", "依赖", "previous case", "chain"]):
                score -= 4
                findings.append("A test case depends on an unstated prerequisite or previous case.")
            if any(token in lowered for token in ["target", "locator", "selector", "元素", "目标"]):
                score -= 3
                findings.append("A step is missing a clear target or locator-oriented objective.")

        deduped = list(dict.fromkeys(item for item in findings if item))
        return result.model_copy(
            update={
                "executability_score": max(score, 0),
                "executability_findings": deduped[:5],
            }
        )

    def _fallback_review_result(self) -> ReviewResult:
        return ReviewResult(
            passed=False,
            score=0,
            comments=[],
            suggestions=[],
            executability_score=0,
            executability_findings=["Reviewer fallback produced no reliable assessment."],
        )

    def _group_cases_by_requirement(self, test_cases: List[TestCase]) -> Dict[str, List[TestCase]]:
        groups: Dict[str, List[TestCase]] = {}
        for case in test_cases:
            groups.setdefault(case.requirement_id, []).append(case)
        return groups

    def _generate_summary(self, details: List[RequirementReviewDetail]) -> str:
        if not details:
            return "No requirements were available for review."
        passed_count = sum(1 for detail in details if detail.passed)
        average_executability = round(
            sum(detail.executability_score or 0 for detail in details) / len(details),
            1,
        )
        return (
            f"Reviewed {len(details)} requirements; {passed_count} passed. "
            f"Average executability score: {average_executability}/20."
        )

