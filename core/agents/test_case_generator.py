"""Test-case generation agent driven by explicit strategy context."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from core.models.requirement import Priority, Requirement, RequirementType
from core.models.test_case import TestCase, TestCaseGenerationResult, TestCaseType, TestStep
from core.utils.llm_client import get_llm_client


class TestCaseGenerator:
    """Generate structured test cases from a requirement and its strategy."""

    def __init__(self):
        self.llm = get_llm_client()

    def generate(
        self,
        requirement: Union[Dict[str, Any], Requirement],
        improvement_hints: Optional[List[str]] = None,
        generation_context: Optional[Dict[str, Any]] = None,
        strategy_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible dict interface."""
        if isinstance(requirement, dict):
            effective_context = strategy_context or generation_context or requirement.get("generation_context")
            req = self._dict_to_requirement(requirement)
        else:
            effective_context = strategy_context or generation_context
            req = requirement

        result = self.generate_structured(
            req,
            improvement_hints=improvement_hints,
            strategy_context=effective_context,
        )
        return [tc.model_dump(mode="json") for tc in result.test_cases]

    def generate_structured(
        self,
        requirement: Requirement,
        improvement_hints: Optional[List[str]] = None,
        generation_context: Optional[Dict[str, Any]] = None,
        strategy_context: Optional[Dict[str, Any]] = None,
    ) -> TestCaseGenerationResult:
        """Generate test cases with structured output."""
        effective_context = strategy_context or generation_context
        prompt = self._build_prompt(
            requirement,
            improvement_hints,
            generation_context=effective_context,
        )

        try:
            result = self.llm.invoke_structured(
                TestCaseGenerationResult,
                prompt,
                operation=f"test_case_generation_{requirement.id}",
            )

            if isinstance(result, TestCaseGenerationResult):
                structured_result = result
            else:
                structured_result = self._validate_and_convert(result, requirement.id)

            for test_case in structured_result.test_cases:
                test_case.requirement_id = requirement.id
            return self._apply_generation_plan(structured_result, requirement.id, effective_context)
        except ValidationError as exc:
            print(f"[TestCaseGenerator] Structured validation failed: {exc}")
            return self._fallback_invoke(prompt, requirement.id, effective_context)
        except Exception as exc:
            print(f"[TestCaseGenerator] Structured generation failed: {exc}")
            return self._fallback_invoke(prompt, requirement.id, effective_context)

    def _validate_and_convert(self, data: dict, requirement_id: str) -> TestCaseGenerationResult:
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict result, got {type(data).__name__}")

        test_cases = []
        raw_test_cases = data.get("test_cases", [])
        for index, tc_data in enumerate(raw_test_cases, start=1):
            tc_data = self._ensure_test_case_fields(tc_data, requirement_id, index)
            try:
                test_cases.append(TestCase.model_validate(tc_data))
            except ValidationError:
                fixed_tc = self._fix_test_case_data(tc_data, requirement_id, index)
                if fixed_tc:
                    test_cases.append(fixed_tc)

        return TestCaseGenerationResult(
            test_cases=test_cases,
            requirement_id=requirement_id,
            total_count=len(test_cases),
        )

    def _fallback_invoke(
        self,
        prompt: str,
        requirement_id: str,
        strategy_context: Optional[Dict[str, Any]] = None,
    ) -> TestCaseGenerationResult:
        print("[TestCaseGenerator] Falling back to plain JSON generation")

        try:
            content = self.llm.chat_simple(prompt, temperature=0.7, max_tokens=4096)
            json_data = self._extract_json(content)
            parsed = self._parse_llm_response(json_data, requirement_id)
            return self._apply_generation_plan(parsed, requirement_id, strategy_context)
        except Exception as exc:
            print(f"[TestCaseGenerator] Plain JSON generation also failed: {exc}")
            return self._apply_generation_plan(
                TestCaseGenerationResult(test_cases=[], requirement_id=requirement_id, total_count=0),
                requirement_id,
                strategy_context,
            )

    def _dict_to_requirement(self, req_dict: Dict[str, Any]) -> Requirement:
        try:
            return Requirement.model_validate(req_dict)
        except ValidationError:
            priority_value = str(req_dict.get("priority") or "medium")
            type_value = str(req_dict.get("type") or "functional")
            return Requirement(
                id=req_dict.get("id", "REQ_001"),
                title=req_dict.get("title", "Untitled requirement"),
                description=req_dict.get("description", "Requirement description is missing."),
                priority=Priority(priority_value if priority_value in {"high", "medium", "low"} else "medium"),
                type=RequirementType(type_value if type_value in {"functional", "non_functional", "business", "technical"} else "functional"),
                acceptance_criteria=req_dict.get("acceptance_criteria", ["Core flow works correctly."]),
                ui_elements=req_dict.get("ui_elements", []),
            )

    def _build_prompt(
        self,
        requirement: Requirement,
        improvement_hints: Optional[List[str]] = None,
        generation_context: Optional[Dict[str, Any]] = None,
        strategy_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        strategy_context = strategy_context or generation_context
        req_json = requirement.model_dump_json(indent=2)

        hints_section = ""
        if improvement_hints:
            hints_list = "\n".join(f"- {hint}" for hint in improvement_hints)
            hints_section = f"""
Review feedback to address in this regeneration:
{hints_list}

The new test cases must resolve these feedback items.
"""

        planning_section = ""
        count_instruction = "Generate only the compact set of cases required by the requirement."
        if strategy_context:
            target_case_count = strategy_context.get("target_case_count")
            count_instruction = (
                f"You must generate exactly {target_case_count} test cases, no more and no less."
                if target_case_count
                else count_instruction
            )
            planning_json = json.dumps(strategy_context, ensure_ascii=False, indent=2)
            planning_section = f"""
Strategy context:
```json
{planning_json}
```

Generation rules:
1. Cover critical focus points first and expand them according to their coverage_axes.
2. Expand major points next.
3. Keep normal points to essential coverage only.
4. Do not let light points create standalone filler cases. Merge them into smoke or the main-path cases whenever possible.
5. Decide which focus points can share the same case before writing the final JSON.
6. Never add extra cases just because the requirement text is long.
7. {count_instruction}
"""

        return f"""You are a senior QA engineer. Generate executable UI-oriented test cases from the requirement below.
{hints_section}
{planning_section}
Requirement:
{req_json}

Output JSON:
```json
{{
  "test_cases": [
    {{
      "id": "TC_001",
      "requirement_id": "{requirement.id}",
      "title": "Test case title",
      "priority": "high",
      "type": "functional",
      "steps": [
        {{
          "step_number": 1,
          "action": "Action description",
          "data": "Optional data",
          "expected": "Expected result"
        }}
      ],
      "expected": "Final expected result",
      "tags": ["smoke"]
    }}
  ]
}}
```

Validation rules:
1. requirement_id must equal {requirement.id}.
2. Each case needs at least one step, and step_number values must be consecutive starting from 1.
3. Actions must be specific enough for UI automation.
4. Expected results must be concrete and observable.
5. type must be one of functional, ui, api, integration, performance, security.
6. priority must be one of high, medium, low.
7. Cases for the same requirement must not be duplicates.
8. Output JSON only.
"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return json.loads(self._fix_json_format(content))

    def _fix_json_format(self, content: str) -> str:
        content = content.strip()
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        if content.startswith("json"):
            content = content[4:]

        content = content.strip()
        if not content.startswith("{"):
            start = content.find("{")
            if start != -1:
                content = content[start:]
        if not content.endswith("}"):
            end = content.rfind("}")
            if end != -1:
                content = content[: end + 1]
        return content

    def _parse_llm_response(self, json_data: Dict[str, Any], requirement_id: str) -> TestCaseGenerationResult:
        try:
            test_cases = []
            raw_test_cases = json_data.get("test_cases", [])
            for index, tc_data in enumerate(raw_test_cases, start=1):
                tc_data = self._ensure_test_case_fields(tc_data, requirement_id, index)
                try:
                    test_cases.append(TestCase.model_validate(tc_data))
                except ValidationError as exc:
                    print(f"[TestCaseGenerator] Test case {index} validation failed: {exc}")
                    fixed_tc = self._fix_test_case_data(tc_data, requirement_id, index)
                    if fixed_tc:
                        test_cases.append(fixed_tc)

            return TestCaseGenerationResult(
                test_cases=test_cases,
                requirement_id=requirement_id,
                total_count=len(test_cases),
            )
        except ValidationError as exc:
            print(f"[TestCaseGenerator] Result validation failed: {exc}")
            raise

    def _apply_generation_plan(
        self,
        result: TestCaseGenerationResult,
        requirement_id: str,
        strategy_context: Optional[Dict[str, Any]],
    ) -> TestCaseGenerationResult:
        context = strategy_context or {}
        prefix = str(context.get("case_id_prefix") or requirement_id.split("_", 1)[-1])
        target_case_count = int(context.get("target_case_count") or 0)

        test_cases = list(result.test_cases)
        if target_case_count > 0:
            if len(test_cases) > target_case_count:
                test_cases = test_cases[:target_case_count]
            elif len(test_cases) < target_case_count:
                test_cases.extend(
                    self._build_fallback_cases(
                        requirement_id=requirement_id,
                        strategy_context=context,
                        count=target_case_count - len(test_cases),
                    )
                )

        for index, test_case in enumerate(test_cases, start=1):
            test_case.requirement_id = requirement_id
            test_case.id = f"TC_{prefix}_{index:03d}"

        result.test_cases = test_cases
        result.requirement_id = requirement_id
        result.total_count = len(test_cases)

        coverage_focus = context.get("coverage_focus") or []
        if context:
            result.generation_strategy = (
                f"planning_mode={context.get('planning_mode', 'default')}; "
                f"overall_risk={context.get('overall_risk', 'unknown')}; "
                f"coverage_focus={','.join(str(item) for item in coverage_focus)}"
            )
        return result

    def _build_fallback_cases(
        self,
        *,
        requirement_id: str,
        strategy_context: Dict[str, Any],
        count: int,
    ) -> List[TestCase]:
        focus_points = list(strategy_context.get("focus_points") or [])
        ordered_points = self._sort_focus_points(focus_points)
        if not ordered_points:
            ordered_points = [
                {
                    "point_id": f"{requirement_id}_P01",
                    "point_text": "Cover the primary happy path of the requirement.",
                    "focus_level": "normal",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path"],
                }
            ]

        generated: List[TestCase] = []
        for index in range(count):
            point = ordered_points[index % len(ordered_points)]
            title = self._build_fallback_title(point, index=index + 1)
            axes = point.get("coverage_axes") or ["happy_path"]
            steps = [
                TestStep(
                    step_number=1,
                    action="Open the target page or prepare the prerequisite state",
                    expected="The system is ready for the target interaction",
                ),
                TestStep(
                    step_number=2,
                    action=point.get("point_text") or "Execute the core interaction",
                    expected=self._build_step_expectation(point),
                ),
                TestStep(
                    step_number=3,
                    action="Observe the final system feedback",
                    expected=self._build_final_expectation(point),
                ),
            ]
            generated.append(
                TestCase(
                    id=f"TC_FALLBACK_{index + 1:03d}",
                    requirement_id=requirement_id,
                    title=title,
                    priority=self._fallback_priority(point.get("focus_level")),
                    type=TestCaseType.FUNCTIONAL,
                    steps=steps,
                    expected=self._build_final_expectation(point),
                    tags=self._build_tags(point, axes),
                )
            )
        return generated

    def _sort_focus_points(self, focus_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranking = {"critical": 0, "major": 1, "normal": 2, "light": 3}
        return sorted(
            focus_points,
            key=lambda point: (
                ranking.get(str(point.get("focus_level") or "normal"), 2),
                str(point.get("point_id") or ""),
            ),
        )

    def _build_fallback_title(self, point: Dict[str, Any], *, index: int) -> str:
        point_text = str(point.get("point_text") or "Requirement coverage").strip()
        trimmed = point_text[:80]
        return f"Strategy fallback case {index}: {trimmed}"

    def _build_step_expectation(self, point: Dict[str, Any]) -> str:
        axes = point.get("coverage_axes") or ["happy_path"]
        if "negative" in axes:
            return "The system rejects invalid behavior with a clear and observable response"
        if "boundary" in axes:
            return "The system handles the boundary condition predictably"
        if "recovery" in axes:
            return "The system provides a recovery path and remains consistent"
        return "The key interaction completes as defined by the requirement"

    def _build_final_expectation(self, point: Dict[str, Any]) -> str:
        focus_level = str(point.get("focus_level") or "normal")
        if focus_level == "critical":
            return "The high-risk business result is correct, visible, and leaves the system in a consistent state"
        if focus_level == "major":
            return "The important business rule or failure path is validated with an observable result"
        if focus_level == "light":
            return "The lightweight check is covered without expanding scope beyond the main flow"
        return "The expected business outcome is observable and correct"

    def _fallback_priority(self, focus_level: Optional[str]) -> Priority:
        return {
            "critical": Priority.HIGH,
            "major": Priority.HIGH,
            "normal": Priority.MEDIUM,
            "light": Priority.LOW,
        }.get(str(focus_level or "normal"), Priority.MEDIUM)

    def _build_tags(self, point: Dict[str, Any], axes: List[str]) -> List[str]:
        tags = ["strategy"]
        focus_level = str(point.get("focus_level") or "").strip().lower()
        execution_mode = str(point.get("execution_mode") or "").strip().lower()
        if focus_level:
            tags.append(focus_level)
        if execution_mode:
            tags.append(execution_mode)
        tags.extend(str(axis).strip().lower() for axis in axes if str(axis).strip())
        return tags

    def _ensure_test_case_fields(self, tc_data: Dict, requirement_id: str, index: int) -> Dict:
        data = dict(tc_data or {})
        if not data.get("id"):
            data["id"] = f"TC_{index:03d}"
        data["requirement_id"] = requirement_id
        if not data.get("title"):
            data["title"] = f"Test case {index}"
        if not data.get("expected"):
            data["expected"] = "The expected behavior is observed"

        steps = data.get("steps") or []
        if not steps:
            steps = [
                {
                    "step_number": 1,
                    "action": "Execute the target test operation",
                    "expected": "The target behavior is observed",
                }
            ]
        else:
            normalized_steps = []
            for step_index, step in enumerate(steps, start=1):
                normalized_step = dict(step or {})
                normalized_step["step_number"] = step_index
                if not normalized_step.get("expected"):
                    normalized_step["expected"] = "The step succeeds"
                normalized_steps.append(normalized_step)
            steps = normalized_steps

        data["steps"] = steps
        if "tags" not in data:
            data["tags"] = []
        return data

    def _fix_test_case_data(self, tc_data: Dict, requirement_id: str, index: int) -> Optional[TestCase]:
        try:
            fixed_data = self._ensure_test_case_fields(tc_data, requirement_id, index)
            if fixed_data.get("priority") not in {"high", "medium", "low"}:
                fixed_data["priority"] = "medium"
            if fixed_data.get("type") not in {
                "functional",
                "ui",
                "api",
                "integration",
                "performance",
                "security",
            }:
                fixed_data["type"] = "functional"
            return TestCase.model_validate(fixed_data)
        except Exception as exc:
            print(f"[TestCaseGenerator] Unable to repair test case data: {exc}")
            return TestCase(
                id=f"TC_{index:03d}",
                requirement_id=requirement_id,
                title=f"Test case {index}",
                steps=[TestStep(step_number=1, action="Execute the test", expected="The test passes")],
                expected="The test passes",
            )
