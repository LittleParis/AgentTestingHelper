# TestCaseGenerator 详解

## 1. 定位：执行层，生成具体测试用例

```
TestStrategyPlanner (策略层)
    │
    │ 输出: TestStrategyPlan
    │   └── RequirementStrategy
    │         └── FocusPointStrategy
    │
    ▼
CaseBudgetPlanner (预算层)
    │
    │ 输出: List[Dict] with generation_context
    │   └── target_case_count
    │   └── focus_points
    │   └── coverage_focus
    │
    ▼
TestCaseGenerator (执行层)        ← 当前讲解
    │
    │ 输出: List[TestCase]
    │   └── 具体的测试步骤
    │   └── 预期结果
    │   └── 标签
```

---

## 2. 文件位置

| 类型 | 文件路径 |
|------|---------|
| Agent 实现 | `core/agents/test_case_generator.py` |
| 节点定义 | `core/agents/workflow/nodes/generation_nodes.py` |
| 数据模型 | `core/models/test_case.py` |

---

## 3. 入参详解

```python
def generate(
    self,
    requirement: Union[Dict[str, Any], Requirement],              # 参数1
    improvement_hints: Optional[List[str]] = None,                # 参数2
    generation_context: Optional[Dict[str, Any]] = None,          # 参数3
    strategy_context: Optional[Dict[str, Any]] = None,            # 参数4 (别名)
) -> List[Dict[str, Any]]:
```

| 参数 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `requirement` | `Dict \| Requirement` | `CaseBudgetPlanner` 输出 | 需求对象，包含 generation_context |
| `improvement_hints` | `List[str]` | `CaseReviewer` 输出 | 评审改进建议（迭代时使用） |
| `generation_context` | `Dict` | `requirement["generation_context"]` | 生成上下文 |
| `strategy_context` | `Dict` | 同上 | 参数别名 |

---

## 4. generation_context 的使用

TestCaseGenerator 直接消费 `CaseBudgetPlanner` 生成的 `generation_context`：

```python
generation_context = {
    "target_case_count": 6,        # ← 决定生成多少条用例
    "case_id_prefix": "001",       # ← 决定用例ID格式
    "focus_points": [...],         # ← 参考焦点点内容
    "coverage_focus": [...],       # ← 确保覆盖维度
    "overall_risk": "critical"     # ← 参考风险级别
}
```

### 使用方式

| 字段 | 用途 |
|------|------|
| `target_case_count` | 控制生成用例数量（截断/补充） |
| `case_id_prefix` | 生成用例ID：`TC_001_001` |
| `focus_points` | 参考焦点点文本，生成步骤内容 |
| `coverage_focus` | 确保覆盖维度，添加标签 |
| `overall_risk` | 参考风险级别，决定优先级 |

---

## 5. 主执行流程

```python
def generate_structured(self, requirement, improvement_hints, generation_context):
    # 1. 提取 generation_context
    effective_context = strategy_context or generation_context

    # 2. 构建提示词（包含策略上下文）
    prompt = self._build_prompt(requirement, improvement_hints, effective_context)

    # 3. LLM 结构化输出
    try:
        result = self.llm.invoke_structured(TestCaseGenerationResult, prompt)

        # 4. 设置 requirement_id
        for test_case in result.test_cases:
            test_case.requirement_id = requirement.id

        # 5. 应用生成计划（预算约束）
        return self._apply_generation_plan(result, requirement.id, effective_context)

    except ValidationError:
        # 降级方案
        return self._fallback_invoke(prompt, requirement.id, effective_context)
```

---

## 6. 提示词构建（包含策略上下文）

```python
def _build_prompt(self, requirement, improvement_hints, strategy_context):
    req_json = requirement.model_dump_json(indent=2)

    # 评审改进建议（迭代时使用）
    hints_section = ""
    if improvement_hints:
        hints_list = "\n".join(f"- {hint}" for hint in improvement_hints)
        hints_section = f"""
Review feedback to address in this regeneration:
{hints_list}

The new test cases must resolve these feedback items.
"""

    # 策略上下文（核心）
    planning_section = ""
    if strategy_context:
        target_case_count = strategy_context.get("target_case_count")
        count_instruction = f"You must generate exactly {target_case_count} test cases."

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
4. Do not let light points create standalone filler cases.
5. Decide which focus points can share the same case before writing the final JSON.
6. Never add extra cases just because the requirement text is long.
7. {count_instruction}
"""

    return f"""You are a senior QA engineer. Generate executable UI-oriented test cases.
{hints_section}
{planning_section}
Requirement:
{req_json}

Output JSON:
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
"""
```

---

## 7. 预算约束应用

### 7.1 核心方法

```python
def _apply_generation_plan(self, result, requirement_id, strategy_context):
    context = strategy_context or {}
    prefix = str(context.get("case_id_prefix") or requirement_id.split("_", 1)[-1])
    target_case_count = int(context.get("target_case_count") or 0)

    test_cases = list(result.test_cases)

    # ========== 预算约束 ==========
    if target_case_count > 0:
        # 超出预算：截断
        if len(test_cases) > target_case_count:
            test_cases = test_cases[:target_case_count]

        # 不足预算：补充回退用例
        elif len(test_cases) < target_case_count:
            test_cases.extend(
                self._build_fallback_cases(
                    requirement_id=requirement_id,
                    strategy_context=context,
                    count=target_case_count - len(test_cases),
                )
            )

    # ========== 统一ID格式 ==========
    for index, test_case in enumerate(test_cases, start=1):
        test_case.requirement_id = requirement_id
        test_case.id = f"TC_{prefix}_{index:03d}"  # TC_001_001

    return result
```

### 7.2 约束规则

| 情况 | 处理方式 |
|------|---------|
| `len(test_cases) > target_case_count` | 截断，保留前 N 条 |
| `len(test_cases) < target_case_count` | 补充回退用例 |
| `len(test_cases) == target_case_count` | 不处理 |

---

## 8. 回退用例生成

当 LLM 生成的用例数量不足时，使用 focus_points 补充：

```python
def _build_fallback_cases(self, requirement_id, strategy_context, count):
    # 1. 获取 focus_points
    focus_points = list(strategy_context.get("focus_points") or [])

    # 2. 按 focus_level 排序（critical → major → normal → light）
    ordered_points = self._sort_focus_points(focus_points)

    # 3. 如果没有 focus_points，使用默认
    if not ordered_points:
        ordered_points = [{
            "point_id": f"{requirement_id}_P01",
            "point_text": "Cover the primary happy path of the requirement.",
            "focus_level": "normal",
            "execution_mode": "standard",
            "coverage_axes": ["happy_path"],
        }]

    # 4. 生成回退用例
    generated = []
    for index in range(count):
        # 循环使用 focus_points
        point = ordered_points[index % len(ordered_points)]

        # 构建 3 步骤用例
        steps = [
            TestStep(step_number=1, action="Open the target page...", expected="..."),
            TestStep(step_number=2, action=point.get("point_text"), expected="..."),
            TestStep(step_number=3, action="Observe the final system feedback", expected="..."),
        ]

        generated.append(TestCase(
            id=f"TC_FALLBACK_{index + 1:03d}",
            title=f"Strategy fallback case {index + 1}: {point_text[:80]}",
            priority=self._fallback_priority(point.get("focus_level")),
            steps=steps,
            tags=self._build_tags(point, axes),
        ))

    return generated
```

### 8.1 focus_points 排序规则

```python
def _sort_focus_points(self, focus_points):
    ranking = {"critical": 0, "major": 1, "normal": 2, "light": 3}
    return sorted(
        focus_points,
        key=lambda point: (
            ranking.get(point.get("focus_level"), 2),
            point.get("point_id"),
        )
    )
```

**排序结果：** critical → major → normal → light

### 8.2 回退用例优先级映射

```python
def _fallback_priority(self, focus_level):
    return {
        "critical": Priority.HIGH,
        "major": Priority.HIGH,
        "normal": Priority.MEDIUM,
        "light": Priority.LOW,
    }.get(focus_level, Priority.MEDIUM)
```

---

## 9. 输出数据结构

### 9.1 TestCase 模型

```python
class TestCase(BaseModel):
    """测试用例模型"""

    id: str                              # "TC_001_001"
    requirement_id: str                  # "REQ_001"
    title: str                           # "正确登录验证"
    priority: Priority                   # high|medium|low
    type: TestCaseType                   # functional|ui|api|integration|performance|security
    steps: List[TestStep]                # 测试步骤列表
    expected: str                        # 最终预期结果
    tags: List[str]                      # 标签列表
    preconditions: Optional[str]         # 前置条件
    postconditions: Optional[str]        # 后置条件
    estimated_time: Optional[int]        # 预估时间(秒)
```

### 9.2 TestStep 模型

```python
class TestStep(BaseModel):
    """测试步骤"""

    step_number: int                     # 步骤序号，从1开始
    action: str                          # 操作描述
    data: Optional[str]                  # 测试数据
    expected: str                        # 该步骤预期结果
```

### 9.3 TestCaseGenerationResult 模型

```python
class TestCaseGenerationResult(BaseModel):
    """测试用例生成结果"""

    test_cases: List[TestCase]           # 生成的用例列表
    requirement_id: str                  # 关联需求ID
    total_count: int                     # 用例数量
    generation_strategy: Optional[str]   # 生成策略说明
```

---

## 10. 完整生成示例

### 10.1 输入

```python
requirement = {
    "id": "REQ_001",
    "title": "用户登录",
    "description": "用户可以通过用户名和密码登录系统",
    "acceptance_criteria": [
        "正确的用户名和密码可以成功登录",
        "错误的密码显示'密码错误'提示",
        "连续 3 次密码错误锁定账户"
    ],

    "generation_context": {
        "target_case_count": 6,
        "case_id_prefix": "001",
        "focus_points": [
            {"point_id": "REQ_001_P01", "point_text": "正确的...", "focus_level": "normal"},
            {"point_id": "REQ_001_P02", "point_text": "错误的...", "focus_level": "major"},
            {"point_id": "REQ_001_P03", "point_text": "连续...", "focus_level": "critical"},
        ],
        "coverage_focus": ["happy_path", "negative"],
        "overall_risk": "critical"
    }
}
```

### 10.2 输出

```python
test_cases = [
    TestCase(
        id="TC_001_001",
        requirement_id="REQ_001",
        title="正确登录验证",
        priority="medium",
        type="functional",
        steps=[
            TestStep(step_number=1, action="打开登录页面", expected="登录页面显示"),
            TestStep(step_number=2, action="输入正确的用户名", expected="用户名显示"),
            TestStep(step_number=3, action="输入正确的密码", expected="密码掩码显示"),
            TestStep(step_number=4, action="点击登录按钮", expected="登录成功"),
        ],
        expected="用户成功登录，跳转到首页",
        tags=["happy_path", "normal"]
    ),
    TestCase(
        id="TC_001_002",
        requirement_id="REQ_001",
        title="密码错误验证",
        priority="high",
        type="functional",
        steps=[
            TestStep(step_number=1, action="打开登录页面", expected="登录页面显示"),
            TestStep(step_number=2, action="输入正确的用户名", expected="用户名显示"),
            TestStep(step_number=3, action="输入错误的密码", expected="密码掩码显示"),
            TestStep(step_number=4, action="点击登录按钮", expected="显示错误提示"),
        ],
        expected="显示'密码错误'提示",
        tags=["negative", "major"]
    ),
    # ... 更多用例
]
```

---

## 11. 降级方案

### 11.1 三层降级

| 层级 | 触发条件 | 处理方式 |
|------|---------|---------|
| **第一层** | LLM 结构化输出失败 | JSON 手动解析 |
| **第二层** | JSON 解析失败 | 用例数据修复 |
| **第三层** | 完全失败 | 使用 focus_points 生成回退用例 |

### 11.2 降级流程

```python
def _fallback_invoke(self, prompt, requirement_id, strategy_context):
    # 第一层：普通 LLM 调用 + JSON 提取
    try:
        content = self.llm.chat_simple(prompt, temperature=0.7)
        json_data = self._extract_json(content)
        parsed = self._parse_llm_response(json_data, requirement_id)
        return self._apply_generation_plan(parsed, requirement_id, strategy_context)

    except Exception:
        # 第三层：完全失败，使用 focus_points 生成
        return self._apply_generation_plan(
            TestCaseGenerationResult(test_cases=[], requirement_id=requirement_id),
            requirement_id,
            strategy_context,  # ← 使用 focus_points 补充
        )
```

---

## 12. 并行执行机制

TestCaseGenerator 在工作流中以**并行方式**执行，每个需求独立生成用例。

### 12.1 节点实现

```python
# core/agents/workflow/nodes/generation_nodes.py

def generate_test_cases_node(state: AgentState) -> dict:
    """准备并行生成"""
    return {
        "test_cases": Overwrite([]),  # 清空列表
        "current_step": "test_case_generation_dispatched",
    }

def fan_out_requirements(state: AgentState):
    """分发并行任务"""
    requirements = state.get("requirements") or []
    return [
        Send(
            "generate_test_case_for_requirement",
            {
                "requirement": requirement,
                "strategy_context": requirement.get("generation_context"),
                "improvement_hints": improvement_hints,
            }
        )
        for requirement in requirements
    ]

def generate_test_case_for_requirement_node(state) -> dict:
    """单个需求生成用例 [并行执行]"""
    requirement = dict(state["requirement"])

    generator = TestCaseGenerator()
    test_cases = generator.generate(
        requirement,
        improvement_hints=state.get("improvement_hints"),
    )

    return {"test_cases": test_cases}
```

### 12.2 并行流程图

```
generate_test_cases_node (准备)
        │
        │ fan_out_requirements
        ▼
┌───────────────────────────────────────────────────┐
│                   并行执行                          │
│                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │ REQ_001     │  │ REQ_002     │  │ REQ_003     ││
│  │ Generator   │  │ Generator   │  │ Generator   ││
│  │ 6 条用例    │  │ 4 条用例    │  │ 3 条用例    ││
│  └─────────────┘  └─────────────┘  └─────────────┘│
│                                                    │
└───────────────────────────────────────────────────┘
        │
        │ merge_lists (合并)
        ▼
finalize_test_case_generation_node (合并结果)
        │
        │ test_cases: [TC_001_001, TC_001_002, ..., TC_002_001, ...]
        ▼
review_test_cases_node (评审)
```

---

## 13. 迭代改进机制

当评审不通过时，TestCaseGenerator 会接收 `improvement_hints` 进行改进。

### 13.1 improvement_hints 来源

```python
# 来自 CaseReviewer 的评审建议
improvement_hints = [
    "增加密码长度边界值测试",
    "添加账号锁定场景测试",
    "补充网络异常场景测试",
]
```

### 13.2 提示词中的使用

```python
if improvement_hints:
    hints_section = f"""
Review feedback to address in this regeneration:
- 增加密码长度边界值测试
- 添加账号锁定场景测试
- 补充网络异常场景测试

The new test cases must resolve these feedback items.
"""
```

---

## 14. 完整数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  CaseBudgetPlanner 输出                                          │
│                                                                  │
│  {                                                               │
│    "id": "REQ_001",                                              │
│    "title": "用户登录",                                           │
│    "generation_context": {                                       │
│      "target_case_count": 6,                                     │
│      "case_id_prefix": "001",                                    │
│      "focus_points": [                                           │
│        {"point_text": "正确的...", "focus_level": "normal"},     │
│        {"point_text": "错误的...", "focus_level": "major"},      │
│        {"point_text": "连续...", "focus_level": "critical"},     │
│      ],                                                          │
│      "coverage_focus": ["happy_path", "negative"],               │
│      "overall_risk": "critical"                                  │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ TestCaseGenerator.generate()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TestCaseGenerator 处理                                          │
│                                                                  │
│  1. 提取 generation_context                                      │
│                                                                  │
│  2. 构建提示词                                                    │
│     - 包含 focus_points                                          │
│     - 包含 target_case_count                                     │
│     - 包含 coverage_focus                                        │
│                                                                  │
│  3. LLM 生成用例                                                  │
│                                                                  │
│  4. 应用预算约束                                                  │
│     - 截断超出部分                                                │
│     - 补充不足部分（使用 focus_points）                           │
│                                                                  │
│  5. 统一ID格式                                                    │
│     TC_001_001, TC_001_002, ...                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TestCaseGenerator 输出                                          │
│                                                                  │
│  [                                                               │
│    TestCase(                                                     │
│      id="TC_001_001",                                            │
│      requirement_id="REQ_001",                                   │
│      title="正确登录验证",                                        │
│      steps=[...],                                                │
│      tags=["happy_path", "normal"]                               │
│    ),                                                            │
│    TestCase(                                                     │
│      id="TC_001_002",                                            │
│      title="密码错误验证",                                        │
│      steps=[...],                                                │
│      tags=["negative", "major"]                                  │
│    ),                                                            │
│    ...                                                           │
│  ]                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 传递给 CaseReviewer
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CaseReviewer 使用                                               │
│                                                                  │
│  评审用例质量                                                     │
│  - 完整性                                                        │
│  - 覆盖率                                                        │
│  - 合理性                                                        │
│  - 独立性                                                        │
│  - 清晰度                                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 15. 总结

### 一句话定义

**TestCaseGenerator = 策略执行者 + 用例生成器**

### 核心职责

| 职责 | 说明 |
|------|------|
| **消费上下文** | 消费 generation_context |
| **生成用例** | LLM 生成具体测试步骤 |
| **应用预算** | 截断/补充到 target_case_count |
| **统一格式** | 统一用例ID格式 |
| **并行执行** | 每个需求独立生成 |

### 输入输出对比

| 项目 | 输入 | 输出 |
|------|------|------|
| 数据来源 | CaseBudgetPlanner | CaseReviewer |
| 核心数据 | generation_context | TestCase |
| 关键字段 | target_case_count | steps, expected |
| 新增内容 | - | 具体测试步骤 |