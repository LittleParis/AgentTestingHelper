# TestStrategyPlanner 与 CaseBudgetPlanner 数据传递详解

## 1. 整体数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Workflow State (AgentState)                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [Node 1] analyze_requirements_node                                     │
│  输出: requirements: List[Requirement]                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ state["requirements"]
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [Node 2] plan_test_strategy_node                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ TestStrategyPlanner.plan()                                       │   │
│  │   输入: requirement_text, requirements                           │   │
│  │   输出: TestStrategyPlan                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  输出: state["test_strategy"] = TestStrategyPlan.to_dict()             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ state["test_strategy"]
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [Node 3] plan_case_budgets_node                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ CaseBudgetPlanner.plan()                                         │   │
│  │   输入: requirement_text, requirements, strategy_plan            │   │
│  │   输出: List[Dict] with generation_context                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  输出: state["planned_requirements"] = List[Dict]                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 文件位置

| 模块 | 文件路径 |
|------|---------|
| TestStrategyPlanner | `core/agents/test_strategy_planner.py` |
| CaseBudgetPlanner | `core/agents/case_budget_planner.py` |
| 数据模型 | `core/models/test_strategy.py` |
| 降级模块 | `core/agents/strategy/` |

---

## 3. 数据模型关系图

```
TestStrategyPlan (策略层)
│
├── requirement_strategies: List[RequirementStrategy]
│   │
│   ├── requirement_id: str              ──────┐
│   │                                         │ 匹配
│   ├── focus_points: List[FocusPointStrategy> │
│   │   ├── point_id: str                      │
│   │   ├── point_text: str                    │
│   │   ├── focus_level: FocusLevel            │
│   │   ├── execution_mode: ExecutionMode      │
│   │   ├── coverage_axes: List[CoverageAxis]  │
│   │   └── case_weight: int                   │
│   │                                          │
│   ├── overall_risk: OverallRisk             │
│   └── suggested_case_budget: int            │
│                                              │
└── total_suggested_case_budget: int          │
                                               │
                                               ▼
Requirement (需求层)                          │
│                                              │
├── id: str                              ◄─────┘
├── title: str
├── description: str
├── acceptance_criteria: List[str]
└── ...

                    │
                    │ 合并 + 转换
                    ▼

Planned Requirement (预算层)
│
├── id: str
├── title: str
├── ... (原始需求字段)
│
└── generation_context: Dict          ← 新增字段
    ├── target_case_count: int        ← 从策略计算
    ├── case_id_prefix: str
    ├── focus_points: List[Dict]      ← 从策略提取
    ├── coverage_focus: List[str]     ← 从策略提取
    └── overall_risk: str             ← 从策略提取
```

---

## 4. TestStrategyPlanner 详解

### 4.1 核心类结构

```python
class TestStrategyPlanner:
    """规划哪些验收点需要深度覆盖"""

    def __init__(self, config: Optional["StrategyConfig"] = None):
        self.llm = get_llm_client()
        self.config = config or get_settings().get_strategy_config()
        self._fallback_builder = FallbackStrategyBuilder(self.config)  # 降级构建器

    def plan(self, requirement_text: str, analyzed_requirements) -> Dict[str, Any]:
        """向后兼容的字典接口"""
        return self.plan_structured(requirement_text, analyzed_requirements).to_dict()

    def plan_structured(self, requirement_text: str, analyzed_requirements) -> TestStrategyPlan:
        """核心方法：结构化策略规划"""
        # ... 主流程
```

### 4.2 主执行流程

```python
def plan_structured(self, requirement_text, analyzed_requirements) -> TestStrategyPlan:
    # 第一步：转换输入为 Requirement 列表
    requirements = [self._ensure_requirement(item) for item in analyzed_requirements]

    # 边界情况：没有需求
    if not requirements:
        return TestStrategyPlan(...)

    # 第二步：构建提示词
    prompt = self._build_prompt(requirement_text, requirements)

    # 第三步：LLM 结构化输出
    try:
        result = self.llm.invoke_structured(TestStrategyPlan, prompt, ...)
        plan = result if isinstance(result, TestStrategyPlan) else TestStrategyPlan.model_validate(result)
        return self._normalize_plan(plan, requirements)  # 标准化
    except Exception:
        return self._fallback_plan(requirement_text, requirements)  # 降级
```

### 4.3 输出数据结构

```python
TestStrategyPlan(
    strategy_version="v1",
    overall_summary="用户登录功能测试策略",

    requirement_strategies=[
        RequirementStrategy(
            requirement_id="REQ_001",           # ← 关键：用于匹配需求

            focus_points=[                      # ← 关键：焦点点列表
                FocusPointStrategy(
                    point_id="REQ_001_P01",
                    point_text="正确的用户名和密码可以成功登录",
                    focus_level=FocusLevel.NORMAL,    # ← 用于计算用例贡献
                    execution_mode=ExecutionMode.STANDARD,
                    coverage_axes=[CoverageAxis.HAPPY_PATH],  # ← 用于覆盖维度
                    case_weight=1,
                ),
                FocusPointStrategy(
                    point_id="REQ_001_P02",
                    point_text="错误的密码显示'密码错误'提示",
                    focus_level=FocusLevel.MAJOR,      # ← major 级别
                    execution_mode=ExecutionMode.STANDARD,
                    coverage_axes=[CoverageAxis.HAPPY_PATH, CoverageAxis.NEGATIVE],
                    case_weight=2,
                ),
                FocusPointStrategy(
                    point_id="REQ_001_P03",
                    point_text="连续 3 次密码错误锁定账户",
                    focus_level=FocusLevel.CRITICAL,   # ← critical 级别
                    execution_mode=ExecutionMode.DEEP,
                    coverage_axes=[CoverageAxis.HAPPY_PATH, CoverageAxis.NEGATIVE],
                    case_weight=3,
                ),
            ],

            overall_risk=OverallRisk.CRITICAL,   # ← 用于风险标记
            suggested_case_budget=6,             # ← 建议用例数
            strategy_summary="登录功能包含安全相关验证...",
        )
    ],

    total_suggested_case_budget=6,
    fallback_used=False,
)
```

### 4.4 降级方案：启发式规则

当 LLM 结构化输出失败时，使用关键词匹配规则：

```python
def _fallback_plan(self, requirement_text, requirements, reason):
    multi_flow = len(requirements) > 1
    strategies = [
        self._fallback_builder.build_requirement_strategy(requirement, multi_flow=multi_flow)
        for requirement in requirements
    ]
    return TestStrategyPlan(
        overall_summary="由于 LLM 策略规划不可用，当前结果由本地启发式规则回退生成...",
        requirement_strategies=strategies,
        ...
    )
```

---

## 5. CaseBudgetPlanner 详解

### 5.1 核心类结构

```python
class CaseBudgetPlanner:
    """将策略输出转换为运行时友好的生成预算"""

    def __init__(self, config: Optional["StrategyConfig"] = None):
        self.config = config or get_settings().get_strategy_config()
        self._strategy_planner: Optional[TestStrategyPlanner] = None  # 可选的内部策略规划器

    def plan(
        self,
        requirement_text: str,
        analyzed_requirements: Optional[List[Dict[str, Any]]] = None,
        strategy_plan: Optional[Dict[str, Any] | TestStrategyPlan] = None,  # ← 从 test_strategy 传入
        page_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """返回带有 generation_context 的需求列表"""
```

### 5.2 主执行流程

```python
def plan(self, requirement_text, analyzed_requirements, strategy_plan, page_url):
    # ========== 第一步：准备需求列表 ==========
    requirements = [self._ensure_requirement_dict(item) for item in (analyzed_requirements or [])]

    # ========== 第二步：解析策略计划 ==========
    parsed_strategy = self._parse_strategy_plan(strategy_plan)

    # 如果没有策略计划，内部调用 TestStrategyPlanner 生成
    if parsed_strategy is None or not parsed_strategy.requirement_strategies:
        if self._strategy_planner is None:
            self._strategy_planner = TestStrategyPlanner(self.config)
        parsed_strategy = self._strategy_planner.plan_structured(
            requirement_text,
            [Requirement.model_validate(r) for r in requirements],
        )

    # ========== 第三步：从策略生成预算 ==========
    planned = self._plan_from_strategy(requirements, parsed_strategy, page_url=page_url)

    # ========== 第四步：添加 E2E 需求（多流程文档） ==========
    if len(requirements) > 1:
        planned.append(self._build_e2e_requirement(requirements, page_url=page_url))

    # ========== 第五步：总预算上限控制 ==========
    self._cap_total_case_budget(planned)

    return planned
```

### 5.3 策略到预算的转换

```python
def _plan_from_strategy(self, requirements, strategy_plan, page_url):
    planned = []

    for requirement in requirements:
        # ========== 关键：通过 requirement_id 匹配策略 ==========
        requirement_strategy = strategy_plan.get_strategy_for_requirement(requirement["id"])

        if requirement_strategy is None:
            continue  # 策略中找不到对应需求，跳过

        # ========== 构建 generation_context ==========
        planned.append(
            self._decorate_requirement(
                requirement=requirement,
                generation_context=self._build_generation_context(
                    requirement=requirement,
                    strategy=requirement_strategy,  # ← 传入匹配的策略
                ),
                page_url=page_url,
            )
        )

    return planned
```

### 5.4 generation_context 构建

```python
def _build_generation_context(self, requirement, strategy):
    # ========== 1. 计算目标用例数 ==========
    # 遍历所有焦点点，累加用例贡献
    budget = sum(
        self._focus_point_case_contribution(point)  # ← 根据焦点级别计算
        for point in strategy.focus_points
    )

    max_budget = self.config.max_budget_per_requirement  # 默认 6

    # 取策略建议值和计算值的较大者，但不超过上限
    target_case_count = max(1, min(max(budget, strategy.suggested_case_budget), max_budget))

    # ========== 2. 提取焦点点 ==========
    focus_points = [point.model_dump(mode="json") for point in strategy.focus_points]

    # ========== 3. 收集覆盖维度 ==========
    coverage_focus = self._collect_coverage_axes(strategy.focus_points)

    # ========== 4. 返回生成上下文 ==========
    return {
        "target_case_count": target_case_count,   # 目标用例数
        "case_id_prefix": str(requirement["id"]).split("_", 1)[-1],  # "001"
        "focus_points": focus_points,             # 焦点点列表
        "coverage_focus": coverage_focus,         # 覆盖维度
        "overall_risk": strategy.overall_risk.value,  # 整体风险
    }
```

### 5.5 焦点点用例贡献计算

```python
def _focus_point_case_contribution(self, point: FocusPointStrategy) -> int:
    """
    根据焦点级别和执行模式计算用例贡献数

    规则：
    - CRITICAL + DEEP  → 3 条用例
    - CRITICAL + 其他   → 2 条用例
    - MAJOR + DEEP     → 2 条用例
    - MAJOR + 其他      → 1 条用例
    - NORMAL           → 1 条用例
    - LIGHT            → 0 条用例（合并到其他用例）
    """
    if point.focus_level == FocusLevel.CRITICAL:
        return 3 if point.execution_mode == ExecutionMode.DEEP else 2
    if point.focus_level == FocusLevel.MAJOR:
        return 2 if point.execution_mode == ExecutionMode.DEEP else 1
    if point.focus_level == FocusLevel.NORMAL:
        return 1
    return 0  # light 级别不单独贡献用例
```

---

## 6. 用例贡献计算规则表

| focus_level | execution_mode | 用例贡献 | 说明 |
|-------------|----------------|---------|------|
| **critical** | deep | 3 | 最高优先级，深度测试 |
| **critical** | standard/smoke | 2 | 最高优先级，标准测试 |
| **major** | deep | 2 | 高优先级，深度测试 |
| **major** | standard/smoke | 1 | 高优先级，标准测试 |
| **normal** | 任意 | 1 | 普通优先级 |
| **light** | 任意 | 0 | 低优先级，合并到其他用例 |

---

## 7. 完整数据传递示例

### 7.1 输入数据（来自 analyze_requirements_node）

```python
requirements = [
    {
        "id": "REQ_001",
        "title": "用户登录",
        "description": "用户可以通过用户名和密码登录系统",
        "acceptance_criteria": [
            "正确的用户名和密码可以成功登录",
            "错误的密码显示'密码错误'提示",
            "连续 3 次密码错误锁定账户"
        ]
    }
]
```

### 7.2 TestStrategyPlanner 输出

```python
test_strategy = {
    "strategy_version": "v1",
    "overall_summary": "用户登录功能测试策略",
    "requirement_strategies": [
        {
            "requirement_id": "REQ_001",
            "focus_points": [
                {
                    "point_id": "REQ_001_P01",
                    "point_text": "正确的用户名和密码可以成功登录",
                    "focus_level": "normal",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path"],
                    "case_weight": 1
                },
                {
                    "point_id": "REQ_001_P02",
                    "point_text": "错误的密码显示'密码错误'提示",
                    "focus_level": "major",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path", "negative"],
                    "case_weight": 2
                },
                {
                    "point_id": "REQ_001_P03",
                    "point_text": "连续 3 次密码错误锁定账户",
                    "focus_level": "critical",
                    "execution_mode": "deep",
                    "coverage_axes": ["happy_path", "negative"],
                    "case_weight": 3
                }
            ],
            "overall_risk": "critical",
            "suggested_case_budget": 6,
            "strategy_summary": "登录功能包含安全相关验证..."
        }
    ],
    "total_suggested_case_budget": 6,
    "fallback_used": False
}
```

### 7.3 CaseBudgetPlanner 转换过程

```python
# 1. 匹配策略
requirement_strategy = strategy_plan.get_strategy_for_requirement("REQ_001")
# 找到匹配的策略

# 2. 计算用例贡献
# P01: normal → 1
# P02: major + standard → 1
# P03: critical + deep → 3
# 总计: 1 + 1 + 3 = 5

# 3. 取最大值
target_case_count = max(5, strategy.suggested_case_budget=6)  # = 6
# 但不超过 max_budget_per_requirement = 6

# 4. 收集覆盖维度
coverage_focus = ["happy_path", "negative"]  # 去重后
```

### 7.4 CaseBudgetPlanner 输出

```python
planned_requirements = [
    {
        "id": "REQ_001",
        "title": "用户登录",
        "description": "用户可以通过用户名和密码登录系统",
        "acceptance_criteria": [...],
        "flow_name": "用户登录",
        "flow_type": "setup",
        "page_url": "https://example.com/login",

        # ========== 新增的生成上下文 ==========
        "generation_context": {
            "target_case_count": 6,        # 目标生成 6 条用例
            "case_id_prefix": "001",       # 用例 ID 前缀
            "focus_points": [              # 焦点点列表
                {
                    "point_id": "REQ_001_P01",
                    "point_text": "正确的用户名和密码可以成功登录",
                    "focus_level": "normal",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path"],
                    "case_weight": 1
                },
                {
                    "point_id": "REQ_001_P02",
                    "point_text": "错误的密码显示'密码错误'提示",
                    "focus_level": "major",
                    "execution_mode": "standard",
                    "coverage_axes": ["happy_path", "negative"],
                    "case_weight": 2
                },
                {
                    "point_id": "REQ_001_P03",
                    "point_text": "连续 3 次密码错误锁定账户",
                    "focus_level": "critical",
                    "execution_mode": "deep",
                    "coverage_axes": ["happy_path", "negative"],
                    "case_weight": 3
                }
            ],
            "coverage_focus": ["happy_path", "negative"],
            "overall_risk": "critical"
        }
    }
]
```

---

## 8. 关键数据传递点总结

| 传递点 | 来源 | 目标 | 数据 | 用途 |
|--------|------|------|------|------|
| **requirement_id** | `Requirement.id` | `RequirementStrategy.requirement_id` | 字符串 | 匹配需求和策略 |
| **focus_points** | `RequirementStrategy.focus_points` | `generation_context["focus_points"]` | 列表 | 焦点点信息 |
| **focus_level** | `FocusPointStrategy.focus_level` | 用例贡献计算 | 枚举 | 决定用例数量 |
| **execution_mode** | `FocusPointStrategy.execution_mode` | 用例贡献计算 | 枚举 | 影响用例深度 |
| **coverage_axes** | `FocusPointStrategy.coverage_axes` | `generation_context["coverage_focus"]` | 列表 | 覆盖维度 |
| **overall_risk** | `RequirementStrategy.overall_risk` | `generation_context["overall_risk"]` | 枚举 | 风险标记 |
| **suggested_case_budget** | `RequirementStrategy.suggested_case_budget` | `target_case_count` 参考 | 整数 | 建议用例数 |

---

## 9. 降级方案总结

### 9.1 TestStrategyPlanner 降级

| 触发条件 | 降级方式 | 核心逻辑 |
|---------|---------|---------|
| LLM 结构化输出失败 | 启发式关键词规则 | `FallbackStrategyBuilder.build_requirement_strategy()` |
| LLM 漏掉某个需求 | 单需求降级 | `_normalize_plan()` 中补充降级策略 |

### 9.2 关键词匹配规则

| 级别 | 匹配关键词 | 用例贡献 |
|------|-----------|---------|
| **critical** | 支付、资金、提交、状态变更、权限、安全、失败恢复、回滚、重试、幂等、人工审核、审计、风控 | 3 (deep) 或 2 (standard) |
| **major** | 失败、异常、边界、重试、验证、校验、错误处理、必填、格式、长度、范围 | 2 (deep) 或 1 (standard) |
| **normal** | 无特殊关键词 | 1 |
| **light** | 显示、可见、加载、导航、提示、样式、布局、颜色、字体、图标 | 0 (合并到其他用例) |

---

## 10. 总预算上限控制

当总用例数超过 `max_total_cases`（默认 20）时，按以下规则削减：

```python
def _cap_total_case_budget(self, planned_requirements):
    max_total = self.config.max_total_cases  # 默认 20

    while self._sum_case_budget(planned_requirements) > max_total:
        # 选择最适合削减的需求
        candidate = self._pick_budget_reduction_candidate(planned_requirements)
        if candidate is None:
            break

        # 削减 1 个用例
        context = candidate.get("generation_context")
        context["target_case_count"] -= 1
        context["budget_reduced"] = True
```

### 削减优先级

优先削减以下类型的需求：

1. **light 级别焦点点多的需求**（权重 × 10）
2. **normal 级别焦点点多的需求**（权重 × 6）
3. **低风险需求**（medium → 权重 2，low → 权重 3）
4. **不削减 critical/major 级别焦点点多的需求**（负权重）

---

## 11. E2E 需求自动生成

当文档包含多个需求时，自动生成 E2E 需求：

```python
def _build_e2e_requirement(self, requirements, page_url):
    # 生成需求 ID
    next_requirement_id = self._next_requirement_id(requirements)

    # 构建主路径描述
    titles = [item.get("title") for item in requirements]
    happy_path_text = " -> ".join(titles)  # "用户登录 -> 下单 -> 支付"

    return {
        "id": next_requirement_id,  # "REQ_004"
        "title": "End-to-end main path validation",
        "description": f"Verify the primary business path across {happy_path_text}.",
        "flow_type": "e2e",
        "generation_context": {
            "target_case_count": 1,
            "case_id_prefix": "004",
            "focus_points": [...],
            "coverage_focus": ["happy_path"],
            "overall_risk": "high"
        }
    }
```
