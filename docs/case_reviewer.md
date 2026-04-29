# CaseReviewer 详解

## 1. 定位：质量把关层，决定是否需要重新生成

```
TestStrategyPlanner (策略层)
    │
    ▼
CaseBudgetPlanner (预算层)
    │
    ▼
TestCaseGenerator (执行层)
    │
    │ 输出: List[TestCase]
    │
    ▼
CaseReviewer (评审层)        ← 当前讲解
    │
    │ 输出: ReviewAllResult
    │   └── passed: bool
    │   └── score: int
    │   └── suggestions: List[str]
    │
    ▼
[条件判断] should_regenerate
    │
    ├── passed=False → 重新生成（迭代）
    └── passed=True → 继续执行
```

---

## 2. 文件位置

| 类型 | 文件路径 |
|------|---------|
| Agent 实现 | `core/agents/case_reviewer.py` |
| 节点定义 | `core/agents/workflow/nodes/review_nodes.py` |
| 数据模型 | `core/models/review.py` |

---

## 3. 入参详解

```python
def review_all(
    self,
    requirements: List[Union[Dict[str, Any], Requirement]],    # 参数1
    all_test_cases: List[Union[Dict[str, Any], TestCase]],     # 参数2
) -> Dict[str, Any]:
```

| 参数 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `requirements` | `List[Requirement]` | `CaseBudgetPlanner` 输出 | 需求列表（含 generation_context） |
| `all_test_cases` | `List[TestCase]` | `TestCaseGenerator` 输出 | 所有生成的测试用例 |

---

## 4. 评审维度（5 个维度，每个 0-20 分）

| 维度 | 英文 | 说明 | 评分标准 |
|------|------|------|---------|
| **完整性** | completeness | 每个用例是否有明确步骤、预期结果、是否覆盖验收标准 | 步骤完整、预期明确、验收标准覆盖 |
| **覆盖率** | coverage | 正向场景、异常场景、边界条件是否覆盖 | happy_path、negative、boundary |
| **合理性** | reasonability | 测试步骤是否合理、预期结果是否明确、用例是否可执行 | 逻辑正确、预期可验证 |
| **独立性** | independence | 用例之间是否独立、是否有依赖关系、是否可以单独执行 | 无前置依赖、可独立运行 |
| **清晰度** | clarity | 描述是否清晰、步骤是否具体、是否易于理解 | 步骤具体、描述清晰 |

**总分：0-100 分（5 个维度之和）**

---

## 5. 可执行性评分（独立维度，不计入总分）

除了 5 个评审维度，还有一个独立的**可执行性评分**：

```python
executability_score: 0-20  # 不计入 score
executability_findings: List[str]  # 具体问题
```

### 5.1 可执行性关注点

| 问题类型 | 说明 | 扣分 |
|---------|------|------|
| **模糊预期** | 预期结果太模糊，无法确定性验证 | -3 |
| **隐藏依赖** | 用例依赖未说明的前置条件或前一个用例 | -4 |
| **缺少目标** | 步骤缺少明确的 UI 元素或操作目标 | -3 |

### 5.2 检测关键词

```python
def _normalize_executability(self, result):
    for comment in result.comments:
        lowered = comment.message.lower()

        # 模糊预期
        if any(token in lowered for token in ["vague", "模糊", "normal", "successfully", "正常", "成功"]):
            score -= 3
            findings.append("Expected result wording is too vague for deterministic execution.")

        # 隐藏依赖
        if any(token in lowered for token in ["dependency", "前置", "依赖", "previous case", "chain"]):
            score -= 4
            findings.append("A test case depends on an unstated prerequisite or previous case.")

        # 缺少目标
        if any(token in lowered for token in ["target", "locator", "selector", "元素", "目标"]):
            score -= 3
            findings.append("A step is missing a clear target or locator-oriented objective.")
```

---

## 6. 主执行流程

### 6.1 单需求评审

```python
def review_structured(self, requirement: Requirement, test_cases: List[TestCase]) -> ReviewResult:
    # 1. 构建评审提示词
    prompt = self._build_review_prompt(requirement, test_cases)

    # 2. LLM 结构化输出
    try:
        result = self.llm.invoke_structured(ReviewResult, prompt, ...)
        return self._normalize_executability(result)  # 标准化可执行性评分
    except ValidationError:
        return self._fallback_invoke(prompt)  # 降级方案
```

### 6.2 全需求评审

```python
def review_all_structured(self, requirements, all_test_cases) -> ReviewAllResult:
    # 1. 按需求分组用例
    grouped_cases = self._group_cases_by_requirement(all_test_cases)

    details = []
    total_score = 0

    # 2. 逐个需求评审
    for requirement in requirements:
        req_cases = grouped_cases.get(requirement.id, [])

        # 边界情况：没有用例
        if not req_cases:
            details.append(RequirementReviewDetail(
                requirement_id=requirement.id,
                passed=False,
                score=0,
                comments=[ReviewComment(
                    type=CommentType.NO_COVERAGE,
                    severity=CommentSeverity.HIGH,
                    message=f"Requirement {requirement.id} has no generated test cases.",
                )],
                suggestions=["Generate at least one executable case for this requirement."],
            ))
            continue

        # 正常评审
        result = self.review_structured(requirement, req_cases)
        details.append(RequirementReviewDetail(...))
        total_score += result.score

    # 3. 计算平均分
    average_score = total_score / len(requirements)

    # 4. 判断是否通过
    passed = all(detail.passed for detail in details) and average_score >= 60

    # 5. 生成摘要
    summary = self._generate_summary(details)

    return ReviewAllResult(
        passed=passed,
        total_score=round(average_score, 1),
        details=details,
        summary=summary,
    )
```

---

## 7. 评审提示词

```python
def _build_review_prompt(self, requirement, test_cases):
    requirement_json = requirement.model_dump_json(indent=2)
    cases_json = json.dumps([case.model_dump(mode="json") for case in test_cases], ...)

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
```

---

## 8. 输出数据结构

### 8.1 ReviewResult（单需求评审结果）

```python
class ReviewResult(BaseModel):
    passed: bool                              # 是否通过
    score: int                               # 总分 0-100
    dimensions: ReviewDimensions             # 各维度得分
    comments: List[ReviewComment]            # 评审意见
    suggestions: List[str]                   # 改进建议
    executability_score: Optional[int]       # 可执行性评分 0-20
    executability_findings: List[str]        # 可执行性问题
```

### 8.2 ReviewDimensions（维度得分）

```python
class ReviewDimensions(BaseModel):
    completeness: int    # 0-20
    coverage: int        # 0-20
    reasonability: int   # 0-20
    independence: int    # 0-20
    clarity: int         # 0-20

    def total(self) -> int:
        return self.completeness + self.coverage + self.reasonability + self.independence + self.clarity
```

### 8.3 ReviewComment（评审意见）

```python
class ReviewComment(BaseModel):
    type: CommentType           # error|warning|suggestion|no_coverage|parse_error|executability
    severity: CommentSeverity   # high|medium|low
    message: str                # 意见内容
    field: Optional[str]        # 相关字段
```

### 8.4 ReviewAllResult（全需求评审结果）

```python
class ReviewAllResult(BaseModel):
    passed: bool                              # 整体是否通过
    total_score: float                        # 平均分 0-100
    details: List[RequirementReviewDetail]    # 各需求评审详情
    summary: str                              # 评审摘要
```

---

## 9. 评审通过条件

```python
# 单需求通过条件
passed = score >= 60

# 整体通过条件
passed = all(detail.passed for detail in details) and average_score >= 60
```

**通过条件：**
1. 每个需求的评审都通过（score >= 60）
2. 平均分 >= 60

---

## 10. 降级方案

### 10.1 LLM 评审失败 → JSON 解析

```python
def _fallback_invoke(self, prompt: str) -> ReviewResult:
    try:
        response = self.llm.chat_simple(prompt)
        return self._parse_response(response)
    except Exception:
        return self._fallback_review_result()
```

### 10.2 完全失败 → 最小评审结果

```python
def _fallback_review_result(self) -> ReviewResult:
    return ReviewResult(
        passed=False,
        score=0,
        comments=[],
        suggestions=[],
        executability_score=0,
        executability_findings=["Reviewer fallback produced no reliable assessment."],
    )
```

### 10.3 规则评审（workflow 中的 simple_review）

当 LLM 评审完全失败时，使用规则评审：

```python
# core/agents/workflow/scenarios/login_only.py

def simple_review(requirements: List[dict], test_cases: List[dict]) -> dict:
    comments = []
    passed = True
    score = 100

    # 1. 检查覆盖完整性
    requirement_ids = {req["id"] for req in requirements}
    test_case_requirement_ids = set()
    for test_case in test_cases:
        if test_case.get("id", "").startswith("TC_"):
            parts = test_case["id"].split("_")
            if len(parts) > 1:
                test_case_requirement_ids.add(f"REQ_{parts[1]}")

    missing_requirements = requirement_ids - test_case_requirement_ids
    if missing_requirements:
        passed = False
        score -= 20
        comments.append({
            "type": "missing_coverage",
            "severity": "high",
            "message": f"Missing test-case coverage for requirements: {sorted(missing_requirements)}",
        })

    # 2. 检查预期结果
    for test_case in test_cases:
        if not test_case.get("expected"):
            score -= 5
            comments.append({
                "type": "missing_expected",
                "severity": "medium",
                "message": f"{test_case.get('id')} has no expected result.",
            })

    # 3. 检查用例数量
    if len(test_cases) < len(requirements):
        passed = False
        score -= 20
        comments.append({
            "type": "insufficient_cases",
            "severity": "high",
            "message": f"Generated test cases ({len(test_cases)}) are fewer than requirements ({len(requirements)}).",
        })

    return {
        "review_passed": passed,
        "review_score": max(score, 0),
        "review_comments": comments,
        "review_suggestions": [],
    }
```

---

## 11. 迭代改进机制

### 11.1 工作流中的条件判断

```python
# core/agents/workflow/routing.py

def should_regenerate(state: AgentState) -> str:
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 2)

    # 达到最大迭代次数
    if iteration >= max_iterations:
        return "end"

    # 评审通过
    if state.get("review_passed", False):
        return "end"

    # 需要重新生成
    return "regenerate"
```

### 11.2 迭代流程图

```
generate_test_case_for_requirement_node
        │
        ▼
finalize_test_case_generation_node
        │
        ▼
review_test_cases_node
        │
        ▼
┌───────────────────┐
│ should_regenerate │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
"regenerate"  "end"
    │           │
    ▼           ▼
increment_iteration   plan_script_generation
    │
    │ iteration_count += 1
    │ improvement_hints = review_suggestions[:5]
    │
    ▼
generate_test_cases_node（重新生成）
```

### 11.3 improvement_hints 传递

```python
# core/agents/workflow/utils.py

def get_improvement_hints(state: AgentState) -> Optional[List[str]]:
    iteration = state.get("iteration_count", 0)
    review_suggestions = state.get("review_suggestions") or []

    if iteration <= 0 or not review_suggestions:
        return None

    max_hints = 5
    return review_suggestions[:max_hints]  # 最多传递 5 条建议
```

---

## 12. 完整评审示例

### 12.1 输入

```python
requirement = Requirement(
    id="REQ_001",
    title="用户登录",
    acceptance_criteria=[
        "正确的用户名和密码可以成功登录",
        "错误的密码显示'密码错误'提示",
        "连续 3 次密码错误锁定账户"
    ]
)

test_cases = [
    TestCase(
        id="TC_001_001",
        title="正确登录验证",
        steps=[
            TestStep(step_number=1, action="打开登录页面", expected="页面显示"),
            TestStep(step_number=2, action="输入正确用户名密码", expected="输入成功"),
            TestStep(step_number=3, action="点击登录", expected="登录成功"),
        ],
        expected="登录成功",
        tags=["happy_path"]
    ),
    TestCase(
        id="TC_001_002",
        title="密码错误验证",
        steps=[
            TestStep(step_number=1, action="打开登录页面", expected="页面显示"),
            TestStep(step_number=2, action="输入错误密码", expected="输入成功"),
            TestStep(step_number=3, action="点击登录", expected="显示错误"),
        ],
        expected="显示密码错误提示",
        tags=["negative"]
    ),
]
```

### 12.2 输出

```python
ReviewResult(
    passed=True,
    score=72,

    dimensions=ReviewDimensions(
        completeness=14,     # 步骤完整，但缺少账户锁定用例
        coverage=12,         # 缺少边界条件测试
        reasonability=16,    # 步骤合理
        independence=16,     # 用例独立
        clarity=14           # 部分预期结果不够具体
    ),

    comments=[
        ReviewComment(
            type=CommentType.SUGGESTION,
            severity=CommentSeverity.MEDIUM,
            message="缺少账户锁定场景的测试用例"
        ),
        ReviewComment(
            type=CommentType.SUGGESTION,
            severity=CommentSeverity.LOW,
            message="预期结果'登录成功'不够具体，建议明确跳转页面"
        )
    ],

    suggestions=[
        "添加账户锁定场景测试用例",
        "细化预期结果描述"
    ],

    executability_score=16,
    executability_findings=[
        "Expected result '登录成功' is too vague for deterministic execution."
    ]
)
```

---

## 13. 完整数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  TestCaseGenerator 输出                                          │
│                                                                  │
│  test_cases = [                                                  │
│    TestCase(id="TC_001_001", steps=[...], expected="..."),      │
│    TestCase(id="TC_001_002", steps=[...], expected="..."),      │
│    ...                                                           │
│  ]                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ CaseReviewer.review_all()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CaseReviewer 处理                                               │
│                                                                  │
│  1. 按需求分组用例                                                │
│     REQ_001 → [TC_001_001, TC_001_002, ...]                     │
│     REQ_002 → [TC_002_001, ...]                                 │
│                                                                  │
│  2. 逐个需求评审                                                  │
│     - LLM 评审 5 个维度                                          │
│     - 计算可执行性评分                                            │
│     - 生成改进建议                                                │
│                                                                  │
│  3. 汇总结果                                                      │
│     - 计算平均分                                                  │
│     - 判断是否通过                                                │
│     - 生成摘要                                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CaseReviewer 输出                                               │
│                                                                  │
│  ReviewAllResult(                                                │
│    passed=True,                                                  │
│    total_score=72.5,                                             │
│    details=[                                                     │
│      RequirementReviewDetail(                                    │
│        requirement_id="REQ_001",                                 │
│        passed=True,                                              │
│        score=72,                                                 │
│        dimensions={completeness: 14, ...},                      │
│        suggestions=["添加账户锁定场景测试用例", ...]              │
│      ),                                                          │
│      ...                                                         │
│    ],                                                            │
│    summary="Reviewed 3 requirements; 2 passed. Avg executability: 15/20"│
│  )                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 传递给 should_regenerate
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  条件判断                                                         │
│                                                                  │
│  if passed=True:                                                 │
│      → "end" → plan_script_generation                           │
│  elif iteration >= max_iterations:                               │
│      → "end" → plan_script_generation                           │
│  else:                                                           │
│      → "regenerate" → increment_iteration → generate_test_cases │
│         improvement_hints = suggestions[:5]                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14. 总结

### 一句话定义

**CaseReviewer = 质量把关者 + 迭代触发器**

### 核心职责

| 职责 | 说明 |
|------|------|
| **评审质量** | 评估用例的完整性、覆盖率、合理性、独立性、清晰度 |
| **评估可执行性** | 检查用例是否可以确定性执行 |
| **生成建议** | 提供具体的改进建议 |
| **触发迭代** | 不通过时触发重新生成 |

### 评审维度

| 维度 | 分值 | 关注点 |
|------|------|--------|
| completeness | 0-20 | 步骤完整、预期明确、验收标准覆盖 |
| coverage | 0-20 | happy_path、negative、boundary |
| reasonability | 0-20 | 逻辑正确、预期可验证 |
| independence | 0-20 | 无前置依赖、可独立运行 |
| clarity | 0-20 | 步骤具体、描述清晰 |
| **executability** | 0-20 | 可确定性执行（独立维度） |

### 迭代机制

| 条件 | 结果 |
|------|------|
| `passed=True` | 继续执行 |
| `passed=False && iteration < max_iterations` | 重新生成（传递 improvement_hints） |
| `passed=False && iteration >= max_iterations` | 继续执行（达到最大迭代次数） |
