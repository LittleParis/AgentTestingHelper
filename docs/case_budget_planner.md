# CaseBudgetPlanner 详解

## 1. 定位：策略层到执行层的桥梁

```
TestStrategyPlanner (策略层)
    │
    │ 输出: TestStrategyPlan
    │   └── RequirementStrategy
    │         └── FocusPointStrategy (focus_point)
    │
    ▼
CaseBudgetPlanner (预算层)        ← 当前讲解
    │
    │ 输出: List[Dict] with generation_context
    │
    ▼
TestCaseGenerator (执行层)
```

---

## 2. 文件位置

| 类型 | 文件路径 |
|------|---------|
| Agent 实现 | `core/agents/case_budget_planner.py` |
| 节点定义 | `core/agents/workflow/nodes/planning_nodes.py` |
| 数据模型 | `core/models/test_strategy.py` |

---

## 3. 入参详解

```python
def plan(
    self,
    requirement_text: str,                                              # 参数1
    analyzed_requirements: Optional[List[Dict[str, Any]]] = None,       # 参数2
    strategy_plan: Optional[Dict[str, Any] | TestStrategyPlan] = None,  # 参数3
    page_url: Optional[str] = None,                                     # 参数4
) -> List[Dict[str, Any]]:
```

| 参数 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `requirement_text` | `str` | 原始需求文档 | 用于降级时内部调用策略规划 |
| `analyzed_requirements` | `List[Dict]` | `RequirementAnalyzer` 输出 | 结构化需求列表 |
| `strategy_plan` | `Dict \| TestStrategyPlan` | `TestStrategyPlanner` 输出 | **核心输入**，包含 focus_points |
| `page_url` | `str` | 配置/提取 | 页面 URL，写入需求 |

---

## 4. 核心功能：消费 FocusPoints

CaseBudgetPlanner 的核心工作是**消费 TestStrategyPlanner 输出的 focus_points**，计算每个需求应该生成多少条用例。

```
FocusPointStrategy (来自策略层)
│
├── focus_level: critical/major/normal/light    ──┐
├── execution_mode: deep/standard/smoke         ──┼──→ 计算用例贡献
├── coverage_axes: [happy_path, negative, ...]  ──┤
└── case_weight: 1/2/3                          ──┘
                                                  │
                                                  ▼
                                         target_case_count
```

---

## 5. 用例贡献计算规则

### 5.1 计算方法

```python
def _focus_point_case_contribution(self, point: FocusPointStrategy) -> int:
    """
    根据 focus_level 和 execution_mode 计算该焦点点的用例贡献
    """
    if point.focus_level == FocusLevel.CRITICAL:
        return 3 if point.execution_mode == ExecutionMode.DEEP else 2
    if point.focus_level == FocusLevel.MAJOR:
        return 2 if point.execution_mode == ExecutionMode.DEEP else 1
    if point.focus_level == FocusLevel.NORMAL:
        return 1
    return 0  # light 不贡献
```

### 5.2 计算规则表

| focus_level | execution_mode | 用例贡献 |
|-------------|----------------|---------|
| **critical** | deep | 3 |
| **critical** | standard/smoke | 2 |
| **major** | deep | 2 |
| **major** | standard/smoke | 1 |
| **normal** | 任意 | 1 |
| **light** | 任意 | 0 |

---

## 6. 完整计算流程示例

### 6.1 输入：TestStrategyPlanner 输出的 focus_points

```python
focus_points = [
    FocusPointStrategy(
        point_id="REQ_001_P01",
        point_text="正确的用户名和密码可以成功登录",
        focus_level="normal",
        execution_mode="standard",
        case_weight=1,
    ),
    FocusPointStrategy(
        point_id="REQ_001_P02",
        point_text="错误的密码显示'密码错误'提示",
        focus_level="major",
        execution_mode="standard",
        case_weight=2,
    ),
    FocusPointStrategy(
        point_id="REQ_001_P03",
        point_text="连续 3 次密码错误锁定账户",
        focus_level="critical",
        execution_mode="deep",
        case_weight=3,
    ),
]
```

### 6.2 计算过程

```python
# 遍历每个 focus_point，累加用例贡献
budget = sum(
    self._focus_point_case_contribution(point)
    for point in strategy.focus_points
)

# P01: normal + standard → 1
# P02: major + standard → 1
# P03: critical + deep → 3
# 总计: 1 + 1 + 3 = 5
```

### 6.3 与策略建议值取较大者

```python
target_case_count = max(budget, strategy.suggested_case_budget)
# max(5, 6) = 6
```

### 6.4 不超过上限

```python
max_budget = self.config.max_budget_per_requirement  # 默认 6
target_case_count = min(target_case_count, max_budget)
# min(6, 6) = 6
```

---

## 7. generation_context 构建

### 7.1 构建方法

```python
def _build_generation_context(self, requirement, strategy):
    # 1. 计算目标用例数
    budget = sum(
        self._focus_point_case_contribution(point)
        for point in strategy.focus_points
    )
    target_case_count = max(1, min(max(budget, strategy.suggested_case_budget), max_budget))

    # 2. 提取 focus_points（转换为字典）
    focus_points = [point.model_dump(mode="json") for point in strategy.focus_points]

    # 3. 收集覆盖维度（去重）
    coverage_focus = self._collect_coverage_axes(strategy.focus_points)

    # 4. 返回生成上下文
    return {
        "target_case_count": target_case_count,   # 目标用例数
        "case_id_prefix": "001",                  # 用例ID前缀
        "focus_points": focus_points,             # 焦点点列表
        "coverage_focus": coverage_focus,         # 覆盖维度
        "overall_risk": strategy.overall_risk.value,  # 整体风险
    }
```

### 7.2 输出示例

```python
generation_context = {
    "target_case_count": 6,
    "case_id_prefix": "001",
    "focus_points": [
        {"point_id": "REQ_001_P01", "point_text": "正确的...", "focus_level": "normal", ...},
        {"point_id": "REQ_001_P02", "point_text": "错误的...", "focus_level": "major", ...},
        {"point_id": "REQ_001_P03", "point_text": "连续...", "focus_level": "critical", ...},
    ],
    "coverage_focus": ["happy_path", "negative"],
    "overall_risk": "critical"
}
```

---

## 8. 覆盖维度收集

从所有 focus_points 中提取并去重 coverage_axes：

```python
def _collect_coverage_axes(self, focus_points: List[FocusPointStrategy]) -> List[str]:
    ordered: List[str] = []
    for point in focus_points:
        for axis in point.coverage_axes:
            axis_value = axis.value  # "happy_path", "negative", ...
            if axis_value not in ordered:
                ordered.append(axis_value)
    return ordered or [CoverageAxis.HAPPY_PATH.value]
```

**示例：**

```
P01: ["happy_path"]
P02: ["happy_path", "negative"]
P03: ["happy_path", "negative"]

结果: ["happy_path", "negative"]  # 去重后
```

---

## 9. 需求装饰：添加元数据

```python
def _decorate_requirement(self, requirement, generation_context, page_url):
    payload = dict(requirement)

    # 添加流程元数据
    payload.setdefault("type", "functional")
    payload["flow_name"] = payload.get("title") or payload["id"]
    payload["flow_type"] = self._classify_flow_type(payload)

    # 添加页面URL
    if page_url and not payload.get("page_url"):
        payload["page_url"] = page_url

    # 添加生成上下文
    payload["generation_context"] = generation_context

    return payload
```

### flow_type 分类规则

| flow_type | 匹配关键词 | 说明 |
|-----------|-----------|------|
| `payment` | 支付、付款、扣款 | 支付流程 |
| `core_business` | 下单、订单 | 核心业务流程 |
| `setup` | 登录、认证 | 前置准备流程 |
| `requirement` | 无特殊关键词 | 普通需求 |

---

## 10. E2E 需求自动生成

当文档包含多个需求时，自动生成 E2E（端到端）需求。

### 10.1 生成逻辑

```python
def _build_e2e_requirement(self, requirements, page_url):
    # 生成新需求ID
    next_requirement_id = self._next_requirement_id(requirements)  # "REQ_004"

    # 构建主路径描述
    titles = [item.get("title") for item in requirements]
    happy_path_text = " -> ".join(titles)  # "用户登录 -> 下单 -> 支付"

    # 创建一个 E2E focus_point
    focus_point = FocusPointStrategy(
        point_id=f"{next_requirement_id}_P01",
        point_text=f"Complete the primary end-to-end path across {happy_path_text}.",
        focus_level=FocusLevel.MAJOR,
        execution_mode=ExecutionMode.SMOKE,
        coverage_axes=[CoverageAxis.HAPPY_PATH],
        reason="Reserve one document-level main-path case across multiple requirements.",
        case_weight=1,
    )

    return {
        "id": next_requirement_id,
        "title": "End-to-end main path validation",
        "description": f"Verify the primary business path across {happy_path_text}.",
        "flow_type": "e2e",
        "generation_context": {
            "target_case_count": 1,
            "case_id_prefix": "004",
            "focus_points": [focus_point.model_dump()],
            "coverage_focus": ["happy_path"],
            "overall_risk": "high",
        }
    }
```

### 10.2 示例

**输入：**

```python
requirements = [
    {"id": "REQ_001", "title": "用户登录"},
    {"id": "REQ_002", "title": "商品下单"},
    {"id": "REQ_003", "title": "在线支付"},
]
```

**输出：**

```python
{
    "id": "REQ_004",
    "title": "End-to-end main path validation",
    "description": "Verify the primary business path across 用户登录 -> 商品下单 -> 在线支付.",
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

---

## 11. 总预算上限控制

当所有需求的 `target_case_count` 之和超过 `max_total_cases`（默认 20）时，按规则削减。

### 11.1 削减逻辑

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

### 11.2 削减优先级计算

```python
def _budget_reduction_score(self, context):
    # E2E 需求不削减
    if context.get("flow_type") == "e2e":
        return -1

    # 统计各级别焦点点数量
    focus_points = context.get("focus_points") or []
    light = sum(1 for p in focus_points if p.get("focus_level") == "light")
    normal = sum(1 for p in focus_points if p.get("focus_level") == "normal")
    major = sum(1 for p in focus_points if p.get("focus_level") == "major")
    critical = sum(1 for p in focus_points if p.get("focus_level") == "critical")

    # 风险惩罚
    risk_penalty = {
        "critical": 0,   # critical 风险不削减
        "high": 1,
        "medium": 2,
        "low": 3,        # low 风险优先削减
    }.get(context.get("overall_risk"), 2)

    # 计算分数（越高越优先削减）
    return light * 10 + normal * 6 + risk_penalty * 2 - major * 2 - critical * 4
```

### 11.3 削减规则

| 优先削减 | 不削减 |
|---------|--------|
| light 级别焦点点多 | critical 级别焦点点多 |
| normal 级别焦点点多 | major 级别焦点点多 |
| 低风险（low/medium） | 高风险（critical/high） |
| - | E2E 需求 |

---

## 12. 完整数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  TestStrategyPlanner 输出                                        │
│                                                                  │
│  RequirementStrategy:                                            │
│    requirement_id: "REQ_001"                                     │
│    focus_points: [                                               │
│      {focus_level: "normal", execution_mode: "standard"},       │
│      {focus_level: "major", execution_mode: "standard"},        │
│      {focus_level: "critical", execution_mode: "deep"},         │
│    ]                                                             │
│    overall_risk: "critical"                                      │
│    suggested_case_budget: 6                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ CaseBudgetPlanner.plan()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CaseBudgetPlanner 处理                                          │
│                                                                  │
│  1. 匹配策略                                                      │
│     strategy_plan.get_strategy_for_requirement("REQ_001")        │
│                                                                  │
│  2. 计算用例贡献                                                  │
│     P01: normal → 1                                              │
│     P02: major + standard → 1                                    │
│     P03: critical + deep → 3                                     │
│     总计: 5                                                      │
│                                                                  │
│  3. 取最大值                                                      │
│     max(5, suggested_budget=6) = 6                               │
│                                                                  │
│  4. 收集覆盖维度                                                  │
│     ["happy_path", "negative"]                                   │
│                                                                  │
│  5. 添加元数据                                                    │
│     flow_type="setup", page_url=...                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CaseBudgetPlanner 输出                                          │
│                                                                  │
│  {                                                               │
│    "id": "REQ_001",                                              │
│    "title": "用户登录",                                           │
│    "flow_name": "用户登录",                                       │
│    "flow_type": "setup",                                         │
│    "page_url": "https://example.com/login",                      │
│                                                                  │
│    "generation_context": {                                       │
│      "target_case_count": 6,                                     │
│      "case_id_prefix": "001",                                    │
│      "focus_points": [...],                                      │
│      "coverage_focus": ["happy_path", "negative"],               │
│      "overall_risk": "critical"                                  │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 传递给 TestCaseGenerator
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TestCaseGenerator 使用                                          │
│                                                                  │
│  generation_context["target_case_count"] → 生成 6 条用例         │
│  generation_context["focus_points"] → 参考焦点点内容              │
│  generation_context["coverage_focus"] → 确保覆盖维度              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13. 总结

### 一句话定义

**CaseBudgetPlanner = 策略消费者 + 预算计算器**

### 核心职责

| 职责 | 说明 |
|------|------|
| **消费策略** | 消费 TestStrategyPlanner 的 focus_points |
| **计算预算** | 计算每个需求的 target_case_count |
| **生成上下文** | 生成 generation_context 供 TestCaseGenerator 使用 |
| **控制上限** | 控制总预算不超过 max_total_cases |
| **生成 E2E** | 多流程文档自动生成端到端需求 |

### 输入输出对比

| 项目 | 输入 | 输出 |
|------|------|------|
| 数据来源 | TestStrategyPlanner | TestCaseGenerator |
| 核心数据 | focus_points | generation_context |
| 关键字段 | focus_level, execution_mode | target_case_count |
| 新增内容 | - | flow_type, flow_name, page_url |
