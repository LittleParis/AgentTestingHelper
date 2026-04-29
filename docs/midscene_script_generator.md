# MidsceneScriptGenerator 详解

## 1. 定位：测试用例到可执行脚本的转换器

```
TestCaseGenerator (用例生成)
    │
    │ 输出: List[TestCase]
    │
    ▼
CaseReviewer (用例评审)
    │
    │ 输出: ReviewAllResult (passed=True)
    │
    ▼
MidsceneScriptGenerator (脚本生成)    ← 当前讲解
    │
    │ 输出: TypeScript 测试脚本 (.spec.ts)
    │
    ▼
TestExecutor (测试执行)
```

---

## 2. 文件位置

| 类型 | 文件路径 |
|------|---------|
| 主生成器 | `core/automation/midscene_generator.py` |
| 规划 Agent | `core/automation/script_planning_agent.py` |
| 代码渲染器 | `core/automation/script_renderer.py` |
| 数据模型 | `core/models/script_plan.py` |

---

## 3. 核心架构：三层组件

```
┌─────────────────────────────────────────────────────────────────┐
│  MidsceneScriptGenerator                                         │
│                                                                  │
│  职责：入口协调、场景检测、降级处理                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ScriptPlanning │  │ScriptRenderer │  │ 场景检测器     │
│    Agent      │  │               │  │               │
│               │  │               │  │               │
│ 结构化规划     │  │ TypeScript    │  │ LOGIN/SEARCH  │
│ LLM 增强      │  │ 代码渲染       │  │ PAYMENT/FORM  │
│ 确定性 baseline│  │               │  │ GENERIC       │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## 4. 混合策略：原生 Playwright + Midscene AI

### 4.1 设计原则

```python
"""
Midscene test script generator.

This module converts generated test cases into Midscene + Playwright scripts.
The generator intentionally uses a hybrid strategy:

- Deterministic UI operations use Playwright directly.
- Perception or semantic checks still use Midscene `ai(...)).
"""
```

### 4.2 执行目标分类

| 执行目标 | 说明 | 示例操作 |
|---------|------|---------|
| `NATIVE` | 纯原生 Playwright | `page.goto()`, `locator.click()` |
| `MIDSCENE_AI` | 纯 AI 语义操作 | `ai("验证登录成功")` |
| `MIXED` | 混合模式 | 原生操作 + AI 验证 |

### 4.3 混合策略示例

```typescript
// 原生操作：确定性高
await page.goto("https://example.com/login");
await identifierInput.fill(loginUsername);
await passwordInput.fill(loginPassword);
await submitButton.click();

// AI 验证：语义检查
await ai("验证登录成功标志可见");
await ai("检查页面显示用户欢迎信息");
```

---

## 5. 场景类型与选择器配置

### 5.1 场景类型枚举

```python
class ScenarioType(Enum):
    """场景类型枚举"""
    LOGIN = "login"           # 登录场景
    SEARCH = "search"         # 搜索场景
    PAYMENT = "payment"       # 支付场景
    FORM = "form"             # 表单场景
    GENERIC = "generic"       # 通用场景
```

### 5.2 场景选择器配置

```python
SCENARIO_SELECTORS = {
    ScenarioType.LOGIN: {
        "identifier": 'input[type="email"]:visible, input[autocomplete="username"]:visible, ...',
        "password": 'input[type="password"]:visible',
        "submit": 'button[type="submit"]:visible, input[type="submit"]:visible, button:visible',
    },
    ScenarioType.SEARCH: {
        "input": '#kw:visible, input[name="wd"]:visible, ...',
        "submit": '#su:visible, input[type="submit"]:visible, button:visible',
    },
    ScenarioType.PAYMENT: {
        "amount": 'input[placeholder*="金额" i]:visible, input[inputmode="decimal"]:visible, ...',
        "submit": 'button:has-text("支付"), button:has-text("确认"), ...',
    },
    ScenarioType.FORM: {
        "input": 'input:visible, textarea:visible',
        "submit": 'button[type="submit"]:visible, input[type="submit"]:visible, button:visible',
    },
    ScenarioType.GENERIC: {
        "input": 'input:visible, textarea:visible',
        "submit": 'button:visible, input[type="submit"]:visible',
    },
}
```

### 5.3 场景检测优先级

```python
def _detect_scenario_type(self, steps, page_url, scenario_config, tc_title):
    # 1. 从配置获取
    if scenario_config:
        config_type = scenario_config.get("scenario_type")
        if config_type:
            return ScenarioType(config_type)

    # 2. 从 URL 判断
    url_lower = str(page_url or "").lower()
    if any(kw in url_lower for kw in ("login", "signin", "auth", "登录")):
        return ScenarioType.LOGIN
    if any(kw in url_lower for kw in ("search", "百度", "google", "bing")):
        return ScenarioType.SEARCH
    if any(kw in url_lower for kw in ("pay", "checkout", "订单", "支付")):
        return ScenarioType.PAYMENT

    # 3. 从测试标题判断
    title_lower = str(tc_title or "").lower()
    if any(kw in title_lower for kw in ("登录", "login", "signin")):
        return ScenarioType.LOGIN
    # ... 更多关键词

    # 4. 从步骤内容判断
    all_actions = " ".join(str(step.get("action", "")) for step in steps).lower()
    if any(kw in all_actions for kw in ("登录", "账号", "用户名", "密码")):
        return ScenarioType.LOGIN
    # ... 更多关键词

    # 5. 默认返回通用场景
    return ScenarioType.GENERIC
```

---

## 6. 主执行流程

### 6.1 入口方法

```python
def generate(
    self,
    test_cases: List[Dict],
    page_url: str = "https://example.com",
    scenario_config: Optional[Dict[str, Any]] = None,
    strategy_plan: Optional[Dict[str, Any]] = None,
    script_plans: Optional[List[Dict[str, Any]] | List[ScriptExecutionPlan]] = None,
) -> str:
    # 1. 生成脚本内容
    script_content = self._generate_script_content(
        test_cases,
        page_url,
        scenario_config=scenario_config,
        strategy_plan=strategy_plan,
        script_plans=script_plans,
    )

    # 2. 写入文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"auto_generated_{timestamp}.spec.ts"
    filepath = os.path.join(self.output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(script_content)

    return filepath
```

### 6.2 脚本内容生成

```python
def _generate_script_content(self, test_cases, page_url, scenario_config, strategy_plan, script_plans):
    # 有策略计划 → 使用 ScriptPlanningAgent + ScriptRenderer
    if strategy_plan is not None or script_plans is not None:
        resolved_plans = self._coerce_script_plans(
            script_plans,
            test_cases=test_cases,
            page_url=page_url,
            scenario_config=scenario_config,
            strategy_plan=strategy_plan,
        )
        return self._renderer.render(resolved_plans)

    # 无策略计划 → 降级到传统生成方式
    parts = [
        self._generate_header(),
        self._generate_imports(),
        self._generate_test_fixture(),
        "",
        self._generate_test_describe(test_cases, page_url, scenario_config=scenario_config),
    ]
    return "\n".join(parts)
```

---

## 7. ScriptPlanningAgent：结构化规划

### 7.1 核心职责

```python
class ScriptPlanningAgent:
    """Build a structured execution plan before rendering code."""
```

将测试用例转换为 `ScriptExecutionPlan` 结构化计划，包含：
- 场景分类
- 执行策略
- 步骤规划
- 断言意图

### 7.2 规划方法

```python
def plan(
    self,
    test_case: Dict[str, Any],
    *,
    strategy_context: Optional[Dict[str, Any]],
    scenario_config: Optional[Dict[str, Any]],
    page_url: str,
) -> ScriptExecutionPlan:
    # 1. 构建确定性 baseline
    baseline = self._build_deterministic_plan(
        test_case=test_case,
        strategy_context=strategy_context,
        scenario_config=scenario_config,
        page_url=page_url,
    )

    # 2. LLM 增强（可选）
    if not self.use_llm or self.llm_client is None:
        return self.validator.validate(baseline, ...)

    try:
        llm_plan = self.llm_client.invoke_structured(
            ScriptExecutionPlan,
            self._build_prompt(test_case, strategy_context, baseline),
            operation="script_execution_planning",
        )
        merged = self._merge_plan(baseline, llm_plan)
        return self.validator.validate(merged, ...)
    except Exception:
        # 降级到 baseline
        return self.validator.validate(baseline, ...)
```

### 7.3 确定性 Baseline 构建

```python
def _build_deterministic_plan(self, test_case, strategy_context, scenario_config, page_url):
    steps = list(test_case.get("steps") or [])

    # 1. 场景分类
    scenario_type = self.scenario_classifier.classify(steps, page_url, ...)

    # 2. 获取选择器目录
    selectors = self.selector_catalog.get_catalog(scenario_type)

    # 3. 凭证策略
    credential_policy = self.credential_policy.resolve(
        scenario_type=scenario_type,
        scenario_config=scenario_config,
        ...
    )

    # 4. 构建场景计划
    scenario_plan = ScenarioPlan(
        scenario_type=scenario_type,
        risk_level=self._infer_risk_level(strategy_context),
        execution_policy=self._infer_execution_policy(execution_mode, scenario_type),
        allow_ai_only=scenario_type not in {"login_only"},
        requires_runtime_credentials=credential_policy["requires_runtime_credentials"],
        selectors=selectors,
        tags=list(test_case.get("tags") or []),
    )

    # 5. 构建设置计划
    setup_plan = ScriptSetupPlan(
        page_url=page_url,
        initial_wait_ms=1500,
        required_env_vars=list(credential_policy["required_env_vars"]),
        mask_locator_aliases=["identifierInput", "passwordInput"] if scenario_type == "login_only" else [],
    )

    # 6. 构建步骤计划
    step_plans = []
    for index, step in enumerate(steps, start=1):
        step_plan = self.action_strategy.plan_step(
            step_number=index,
            action=str(step.get("action", "")),
            data=str(step.get("data", "")),
            expected=str(step.get("expected", "")),
            scenario_type=scenario_type,
            credential_policy=credential_policy,
            focus_hint=focus_hint,
        )
        step_plan.assertion_intents = self.assertion_strategy.build_step_assertions(...)
        step_plans.append(step_plan)

    # 7. 返回完整计划
    return ScriptExecutionPlan(
        testcase_id=str(test_case.get("id") or "TC_XXX"),
        title=str(test_case.get("title") or "Untitled test case"),
        requirement_id=test_case.get("requirement_id"),
        scenario=scenario_plan,
        setup=setup_plan,
        steps=step_plans,
        final_assertions=self.assertion_strategy.build_final_assertions(...),
        fallback_policy=FallbackPolicy.REPAIR_WITH_RULES if self.use_llm else FallbackPolicy.DETERMINISTIC,
        metadata={...},
    )
```

### 7.4 执行策略推断

```python
def _infer_execution_policy(self, execution_mode: str, scenario_type: str) -> ExecutionPolicy:
    if scenario_type == "login_only":
        return ExecutionPolicy.NATIVE_FIRST  # 原生优先
    if execution_mode == "smoke":
        return ExecutionPolicy.NATIVE_FIRST  # 原生优先
    if execution_mode == "deep":
        return ExecutionPolicy.HYBRID_BALANCED  # 混合均衡
    return ExecutionPolicy.HYBRID_BALANCED
```

---

## 8. ScriptRenderer：代码渲染

### 8.1 渲染入口

```python
class ScriptRenderer:
    """Render structured plans into executable TS scripts."""

    def render(self, plans: Iterable[ScriptExecutionPlan]) -> str:
        plan_list = list(plans)
        parts = [
            self._generate_header(),      # 文件头注释
            self._generate_imports(),     # import 语句
            self._generate_test_fixture(), # test fixture 定义
            "",
            self._generate_describe(plan_list),  # test.describe 块
        ]
        return "\n".join(parts)
```

### 8.2 测试用例渲染

```python
def _render_test(self, plan: ScriptExecutionPlan) -> str:
    # 特殊处理：login_only
    if plan.scenario.scenario_type == "login_only":
        return self._render_login_only_test(plan)

    # 标准渲染
    body_lines = self._render_standard_body(plan)
    return f"""  test({self._to_ts_string(f"{plan.testcase_id}: {plan.title}")}, async ({{ page, ai }}, testInfo) => {{
    console.log({self._to_ts_string(f"[TEST-START] {plan.testcase_id}: {plan.title}")});
    try {{
{body_lines}
    }} finally {{
      await attachFinalScreenshot(page, testInfo);
    }}
    console.log({self._to_ts_string(f"[TEST-END] {plan.testcase_id}: {plan.title}")});
  }});"""
```

### 8.3 步骤渲染

```python
def _render_standard_body(self, plan: ScriptExecutionPlan) -> str:
    lines = [
        f"    // scenario_type: {plan.scenario.scenario_type}",
        f"    // execution_policy: {plan.scenario.execution_policy.value}",
        "    console.log('[STEP] Open target page');",
        f"    await page.goto({self._to_ts_string(plan.setup.page_url)});",
        f"    await page.waitForLoadState({self._to_ts_string(plan.setup.wait_for)});",
    ]

    # 渲染定位器
    lines.extend(self._render_locators(plan))

    # 渲染每个步骤
    for step_index, step in enumerate(plan.steps, start=2):
        lines.append(f"    // Step: {step.original_action}")
        lines.extend(self._render_step_action(step))      # 动作
        lines.extend(self._render_step_assertions(step))  # 断言
        lines.append(f"    await attachStepScreenshot(page, '{step_name}', testInfo);")

    # 渲染最终断言
    if plan.final_assertions:
        lines.extend(self._render_assertions(plan.final_assertions, ...))

    return "\n".join(lines)
```

### 8.4 原生操作渲染

```python
def _render_native_operations(self, operations: List[NativeOperation]) -> List[str]:
    lines = []
    for operation in operations:
        if operation.kind == NativeOperationKind.EXPECT_VISIBLE and operation.locator:
            lines.append(f"    await expect({operation.locator}).toBeVisible();")
        elif operation.kind == NativeOperationKind.FILL and operation.locator:
            value_expr = self._build_fill_expression(operation)
            lines.append(f"    await {operation.locator}.fill({value_expr});")
        elif operation.kind == NativeOperationKind.CLICK and operation.locator:
            lines.append(f"    await {operation.locator}.click();")
        elif operation.kind == NativeOperationKind.WAIT_LOAD:
            lines.append("    await page.waitForLoadState('domcontentloaded');")
        elif operation.kind == NativeOperationKind.WAIT_TIMEOUT:
            lines.append(f"    await page.waitForTimeout({operation.timeout_ms or 1000});")
    return lines
```

### 8.5 断言渲染

```python
def _render_assertions(self, assertions: List[AssertionIntent], fallback_prompt: str = "") -> List[str]:
    lines = []
    for assertion in assertions:
        if assertion.kind == AssertionKind.PAGE_BODY_VISIBLE:
            lines.append("    await expect(page.locator('body')).toBeVisible();")
        elif assertion.kind == AssertionKind.LOCATOR_VISIBLE and assertion.locator:
            lines.append(f"    await expect({assertion.locator}).toBeVisible();")
        elif assertion.kind == AssertionKind.VALUE_EMPTY and assertion.locator:
            lines.append(f"    await expect({assertion.locator}).toHaveValue('');")
        elif assertion.kind == AssertionKind.VALUE_NONEMPTY and assertion.locator:
            lines.append(f"    await expect({assertion.locator}).toHaveValue(/.+/);")
        elif assertion.kind == AssertionKind.URL_SAME:
            lines.append("    await expect.poll(() => page.url()).toBe(initialUrl);")
        elif assertion.kind == AssertionKind.URL_CHANGED:
            lines.append("    await expect.poll(() => page.url()).not.toBe(initialUrl);")
        elif assertion.kind == AssertionKind.TEXT_VISIBLE and assertion.expected_value:
            lines.append(f"    await expect(page.getByText('{assertion.expected_value}', {{ exact: false }})).toBeVisible();")

    # 无原生断言时使用 AI
    if not lines and fallback_prompt:
        lines.append(f"    await ai({self._to_ts_string('Verify: ' + fallback_prompt)});")

    return lines
```

---

## 9. 特殊场景：login_only

### 9.1 场景识别

```python
def _is_login_only_scenario(self, scenario_config: Optional[Dict[str, Any]]) -> bool:
    """Return whether the script should use the restricted login template."""
    return (scenario_config or {}).get("scenario_type") == "login_only"
```

### 9.2 受限登录模板

```python
def _render_login_only_test(self, plan: ScriptExecutionPlan) -> str:
    success_value = str(plan.metadata.get("success_signal_value") or "LianLian")
    success_type = str(plan.metadata.get("success_signal_type") or "visual_text_or_logo")
    manual_wait_timeout_ms = int(plan.metadata.get("manual_wait_timeout_ms") or 180000)
    username_env = str(plan.metadata.get("username_env") or "LOGIN_USERNAME")
    password_env = str(plan.metadata.get("password_env") or "LOGIN_PASSWORD")

    body = "\n".join([
        f"    const loginUsername = process.env[{self._to_ts_string(username_env)}];",
        f"    const loginPassword = process.env[{self._to_ts_string(password_env)}];",
        "    if (!loginUsername || !loginPassword) {",
        f"      throw new Error('Missing login credentials. Add identifier/password to the requirement file, or configure {username_env}/{password_env} in .env.');",
        "    }",
        "    const identifierInput = page.locator(...).first();",
        "    const passwordInput = page.locator('input[type=\"password\"]:visible').first();",
        "    const submitButton = page.locator(...).first();",
        f"    const successText = page.getByText({self._to_ts_string(success_value)}, {{ exact: false }});",
        f"    const successLogo = page.locator({self._to_ts_string(success_logo_selector)}).first();",
        "    const successSignal = successLogo.or(successText).first();",
        "    maskedFields = [identifierInput, passwordInput];",
        "    console.log('[STEP] Open login page');",
        f"    await page.goto({self._to_ts_string(plan.setup.page_url)});",
        "    await page.waitForLoadState('domcontentloaded');",
        "    await expect(identifierInput).toBeVisible();",
        "    await expect(passwordInput).toBeVisible();",
        "    await identifierInput.fill(loginUsername);",
        "    await passwordInput.fill(loginPassword);",
        "    await page.screenshot({ path: 'test-results/login-only-before-submit.png', mask: maskedFields });",
        "    await expect(submitButton).toBeVisible();",
        "    await submitButton.click();",
        "    console.log('[MANUAL-WAIT] Waiting for manual verification to complete.');",
        "    await page.waitForLoadState('domcontentloaded');",
        f"    await expect(successSignal).toBeVisible({{ timeout: {manual_wait_timeout_ms} }});",
        "    console.log('[VERIFY] Login success signal detected.');",
        "    // Stop immediately after login success detection. No further actions are allowed.",
    ])

    return f"""  test({self._to_ts_string(f"{plan.testcase_id}: {plan.title}")}, async ({{ page, ai }}, testInfo) => {{
    // scenario_type: login_only
    // forbidden_actions: {forbidden_actions}
    let maskedFields = [];
    try {{
{body}
    }} finally {{
      await attachFinalScreenshot(page, testInfo, {{ mask: maskedFields }});
    }}
  }});"""
```

### 9.3 login_only 特性

| 特性 | 说明 |
|------|------|
| **凭证来源** | 环境变量 `LOGIN_USERNAME` / `LOGIN_PASSWORD` |
| **成功信号** | 可配置 `success_signal.value` 和 `success_signal.type` |
| **人工等待** | `manual_wait_timeout_ms` 默认 180 秒 |
| **截图遮罩** | 用户名和密码字段自动遮罩 |
| **立即停止** | 检测到成功信号后立即停止，不执行后续操作 |

---

## 10. 数据模型

### 10.1 ScriptExecutionPlan

```python
class ScriptExecutionPlan(BaseModel):
    testcase_id: str                              # 测试用例 ID
    title: str                                    # 测试标题
    requirement_id: Optional[str]                 # 需求 ID
    scenario: ScenarioPlan                        # 场景计划
    setup: ScriptSetupPlan                        # 设置计划
    steps: List[ScriptStepPlan]                   # 步骤计划列表
    final_assertions: List[AssertionIntent]       # 最终断言
    fallback_policy: FallbackPolicy               # 降级策略
    metadata: Dict[str, Any]                      # 元数据
```

### 10.2 ScenarioPlan

```python
class ScenarioPlan(BaseModel):
    scenario_type: str                            # 场景类型
    risk_level: str                               # 风险级别
    execution_policy: ExecutionPolicy             # 执行策略
    allow_ai_only: bool                           # 是否允许纯 AI
    requires_runtime_credentials: bool            # 是否需要运行时凭证
    selectors: Dict[str, str]                     # 选择器映射
    tags: List[str]                               # 标签列表
```

### 10.3 ScriptStepPlan

```python
class ScriptStepPlan(BaseModel):
    step_number: int                              # 步骤编号
    original_action: str                          # 原始动作描述
    original_expected: str                        # 原始预期结果
    normalized_data: str                          # 标准化数据
    action_prompt: str                            # AI 动作提示
    verify_prompt: str                            # AI 验证提示
    preferred_executor: ExecutionTarget           # 首选执行器
    native_operations: List[NativeOperation]      # 原生操作列表
    assertion_intents: List[AssertionIntent]      # 断言意图列表
    decision_trace: Optional[PlannerDecisionTrace] # 决策追踪
```

### 10.4 NativeOperation

```python
class NativeOperation(BaseModel):
    kind: NativeOperationKind                     # 操作类型
    locator: Optional[str]                        # 定位器
    value: Optional[str]                          # 值
    runtime_var: Optional[str]                    # 运行时变量
    fallback_value: Optional[str]                 # 降级值
    timeout_ms: Optional[int]                     # 超时时间

class NativeOperationKind(Enum):
    EXPECT_VISIBLE = "expect_visible"             # 可见性断言
    FILL = "fill"                                 # 填充输入
    CLICK = "click"                               # 点击
    WAIT_LOAD = "wait_load"                       # 等待加载
    WAIT_TIMEOUT = "wait_timeout"                 # 等待超时
```

### 10.5 AssertionIntent

```python
class AssertionIntent(BaseModel):
    kind: AssertionKind                           # 断言类型
    locator: Optional[str]                        # 定位器
    expected_value: Optional[str]                 # 预期值
    runtime_var: Optional[str]                    # 运行时变量
    exact: bool = False                           # 是否精确匹配
    regex: Optional[str]                          # 正则表达式

class AssertionKind(Enum):
    PAGE_BODY_VISIBLE = "page_body_visible"       # 页面主体可见
    LOCATOR_VISIBLE = "locator_visible"           # 定位器可见
    VALUE_EMPTY = "value_empty"                   # 值为空
    VALUE_NONEMPTY = "value_nonempty"             # 值非空
    VALUE_EQUALS = "value_equals"                 # 值相等
    URL_SAME = "url_same"                         # URL 不变
    URL_CHANGED = "url_changed"                   # URL 变化
    URL_MATCHES = "url_matches"                   # URL 匹配
    TEXT_VISIBLE = "text_visible"                 # 文本可见
```

---

## 11. 降级方案

### 11.1 LLM 转换失败 → 规则转换

```python
def _convert_steps_with_llm(self, steps: List[Dict]) -> List[Dict]:
    try:
        result = self.llm_client.invoke_structured(ActionConversionResult, prompt, ...)
        return converted_steps
    except Exception as e:
        print(f"[WARNING] LLM 转换失败，使用降级方案: {e}")
        return self._fallback_convert_steps(steps)

def _fallback_convert_steps(self, steps: List[Dict]) -> List[Dict]:
    converted = []
    for step in steps:
        action = step.get("action", "")
        data = self._normalize_step_data(action, step.get("data", ""))
        expected = step.get("expected", "")
        converted.append({
            "original_action": action,
            "action_prompt": self._convert_action_fallback(action, data, expected),
            "verify_prompt": self._convert_expected_fallback(expected),
            "expected_text": expected,
            "data": data,
        })
    return converted
```

### 11.2 动作降级规则

```python
def _convert_action_fallback(self, action: str, data: str, expected: str) -> str:
    action = str(action or "").strip()

    # 数据驱动动作
    if data and data not in {"N/A", "", "无", "登录页面地址"}:
        if "输入" in action or "填写" in action:
            if "邮箱" in action or "用户名" in action or "账号" in action:
                return f'在用户名输入框输入 "{data}"'
            if "密码" in action:
                return '在密码输入框输入内容'
            if "搜索" in action or "关键词" in action:
                return f'在搜索框输入 "{data}"'

    # 动作特定转换
    if "打开" in action or "访问" in action or "导航" in action:
        return "等待页面加载完成"
    if "点击" in action:
        if "登录" in action:
            return "点击登录按钮"
        if "搜索" in action or "百度一下" in action:
            return "点击搜索按钮"
        return "点击页面上的按钮"
    if "输入" in action:
        if "邮箱" in action or "用户名" in action or "账号" in action:
            return "在用户名输入框输入内容"
        if "密码" in action:
            return "在密码输入框输入内容"
        return "在输入框输入内容"

    # 未处理的动作返回空，让原生处理接管
    return ""
```

### 11.3 预期结果降级规则

```python
def _convert_expected_fallback(self, expected: str) -> str:
    expected = str(expected or "").strip()
    if not expected or expected == "N/A":
        return ""

    # 特定预期结果转换
    if "仍停留在登录页面" in expected or "未跳转" in expected:
        return "页面仍停留在当前URL"
    if ("搜索框" in expected or "输入框" in expected) and "可见" in expected:
        return "搜索框元素可见"
    if "历史记录" in expected:
        return "页面显示搜索建议或历史记录"
    if "搜索结果页" in expected or "结果页面" in expected:
        return "页面显示搜索结果"
    if "跳转" in expected or "URL" in expected:
        return "页面URL发生变化"
    if "错误" in expected or "提示" in expected:
        return "页面显示提示信息"

    # 未处理的预期返回空，让原生断言接管
    return ""
```

---

## 12. 原生操作生成

### 12.1 动作生成

```python
def _generate_native_action_lines(self, action: str, data: str, expected: str, use_runtime_password: bool = True) -> List[str]:
    action_text = str(action or "")

    # 清空操作
    if "清空" in action_text or "清除" in action_text:
        if self._mentions_password_field(action_text):
            return ["    await passwordInput.fill('');"]
        if self._mentions_login_identifier(action_text):
            return ["    await identifierInput.fill('');"]
        return ["    await searchInput.fill('');"]

    # 登录标识符输入
    if self._mentions_login_identifier(action_text):
        value_expr = self._build_runtime_fill_expression("runtimeUsername", data_text)
        return [
            "    await expect(identifierInput).toBeVisible();",
            f"    await identifierInput.fill({value_expr});",
        ]

    # 密码输入
    if self._mentions_password_field(action_text):
        if use_runtime_password:
            value_expr = self._build_runtime_fill_expression("runtimePassword", data_text)
        else:
            value_expr = self._to_ts_string(data_text) if data_text else '"WrongPassword123"'
        return [
            "    await expect(passwordInput).toBeVisible();",
            f"    await passwordInput.fill({value_expr});",
        ]

    # 登录提交按钮
    if self._is_login_submit_action(action_text):
        return [
            "    await expect(submitButton).toBeVisible();",
            "    await submitButton.click();",
        ]

    # 页面导航
    if any(kw in action_text for kw in ("打开", "访问", "导航", "进入")):
        return [
            "    await page.waitForLoadState('domcontentloaded');",
            "    await page.waitForTimeout(1000);",
        ]

    # 未处理的动作返回空，使用 AI
    return []
```

### 12.2 验证生成

```python
def _generate_native_verify_lines(self, action, data, expected, verify_prompt, scenario_type) -> List[str]:
    action_text = str(action or "")
    expected_text = str(expected or "")
    verify_text = str(verify_prompt or "")
    combined_text = " ".join([action_text, expected_text, verify_text])

    # 通用断言：页面URL不变
    if self._is_same_page_assertion(action_text, expected_text, verify_text):
        return ["    await expect.poll(() => page.url()).toBe(initialUrl);"]

    # 通用断言：URL变化
    if self._is_url_assertion(verify_text):
        return self._generate_native_url_assertions(verify_text)

    # 根据场景类型生成特定断言
    if scenario_type == ScenarioType.LOGIN:
        return self._generate_login_verify_lines(...)
    elif scenario_type == ScenarioType.SEARCH:
        return self._generate_search_verify_lines(...)
    elif scenario_type == ScenarioType.PAYMENT:
        return self._generate_payment_verify_lines(...)
    else:
        return self._generate_generic_verify_lines(...)
```

---

## 13. 完整数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  TestCaseGenerator 输出                                          │
│                                                                  │
│  test_cases = [                                                  │
│    {                                                             │
│      "id": "TC_001",                                             │
│      "title": "用户正常登录",                                     │
│      "steps": [                                                  │
│        {"action": "输入用户名", "data": "admin"},                │
│        {"action": "输入密码", "data": "password123"},            │
│        {"action": "点击登录按钮", "expected": "登录成功"},        │
│      ],                                                          │
│      "expected": "跳转到主界面",                                  │
│      "tags": ["smoke", "login"],                                 │
│    }                                                             │
│  ]                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MidsceneScriptGenerator.generate()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  MidsceneScriptGenerator 处理                                    │
│                                                                  │
│  1. 场景检测                                                     │
│     _detect_scenario_type() → ScenarioType.LOGIN                │
│                                                                  │
│  2. 选择器获取                                                   │
│     SCENARIO_SELECTORS[LOGIN] → {identifier, password, submit}  │
│                                                                  │
│  3. 步骤转换                                                     │
│     _convert_steps_with_llm() 或 _fallback_convert_steps()      │
│                                                                  │
│  4. 原生操作生成                                                 │
│     _generate_native_action_lines() → Playwright 代码           │
│                                                                  │
│  5. 验证生成                                                     │
│     _generate_native_verify_lines() → expect() 断言             │
│                                                                  │
│  6. 脚本组装                                                     │
│     _generate_test_function() → 完整测试函数                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  生成的 TypeScript 脚本                                          │
│                                                                  │
│  test('TC_001: 用户正常登录', async ({ page, ai }, testInfo) => {│
│    // 场景类型: login                                            │
│    console.log('[TEST-START] TC_001: 用户正常登录');             │
│    try {                                                         │
│      // 打开目标页面                                             │
│      await page.goto('https://example.com/login');              │
│      await page.waitForLoadState('domcontentloaded');           │
│                                                                  │
│      // 定义定位器                                               │
│      const identifierInput = page.locator(...).first();         │
│      const passwordInput = page.locator(...).first();           │
│      const submitButton = page.locator(...).first();            │
│                                                                  │
│      // 步骤 1: 输入用户名                                        │
│      await expect(identifierInput).toBeVisible();               │
│      await identifierInput.fill(runtimeUsername || 'admin');    │
│                                                                  │
│      // 步骤 2: 输入密码                                          │
│      await expect(passwordInput).toBeVisible();                 │
│      await passwordInput.fill(runtimePassword || 'password');   │
│                                                                  │
│      // 步骤 3: 点击登录按钮                                      │
│      await expect(submitButton).toBeVisible();                  │
│      await submitButton.click();                                │
│                                                                  │
│      // 最终验证                                                 │
│      await ai('验证登录成功标志可见');                            │
│    } finally {                                                   │
│      await attachFinalScreenshot(page, testInfo);               │
│    }                                                             │
│  });                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14. 总结

### 一句话定义

**MidsceneScriptGenerator = 测试用例到可执行脚本的转换器**

### 核心职责

| 职责 | 说明 |
|------|------|
| **场景检测** | 根据配置、URL、标题、步骤内容检测场景类型 |
| **混合策略** | 原生 Playwright 确定性操作 + Midscene AI 语义检查 |
| **结构化规划** | ScriptPlanningAgent 生成 ScriptExecutionPlan |
| **代码渲染** | ScriptRenderer 渲染 TypeScript 测试脚本 |
| **降级处理** | LLM 失败时使用规则转换 |

### 混合策略

| 执行目标 | 适用场景 | 示例 |
|---------|---------|------|
| `NATIVE` | 确定性操作 | 页面导航、输入填充、按钮点击 |
| `MIDSCENE_AI` | 语义检查 | 验证登录成功、检查提示信息 |
| `MIXED` | 混合场景 | 原生操作 + AI 验证 |

### 场景类型

| 场景类型 | 选择器 | 特殊处理 |
|---------|--------|---------|
| `LOGIN` | identifier, password, submit | 运行时凭证、密码遮罩 |
| `SEARCH` | input, submit | 搜索结果验证 |
| `PAYMENT` | amount, submit | 金额输入验证 |
| `FORM` | input, submit | 表单提交验证 |
| `GENERIC` | input, submit | 通用处理 |
| `login_only` | 同 LOGIN | 受限登录、成功信号检测、立即停止 |

### 降级方案

| 层级 | 触发条件 | 处理方式 |
|------|---------|---------|
| 第一层 | LLM 步骤转换失败 | 规则转换 `_fallback_convert_steps()` |
| 第二层 | 无策略计划 | 传统生成方式 `_generate_test_describe()` |
| 第三层 | 无原生操作 | 使用 AI `ai(...)` |
