# Issue #2: bug修复

| 属性 | 值 |
|------|-----|
| 状态 | 🟢 open |
| 标签 | 无标签 |
| 创建时间 | 2026-04-20 |
| 更新时间 | 2026-04-20 |
| 关闭时间 | 未关闭 |
| 评论数 | 0 |
| 链接 | [https://github.com/LittleParis/AgentTestingHelper/issues/2](https://github.com/LittleParis/AgentTestingHelper/issues/2) |

---

## 内容

# Agent 优化 Issues

> 基于当前代码分析，整理以下优化方向，按优先级排序。

---

## Issue 1：用结构化输出替换手动 JSON 解析

**标签**: `enhancement` `tech-debt` `priority-high`

### 问题描述

当前每个 Agent（`RequirementAnalyzer`、`TestCaseGenerator`、`CaseReviewer`）都有大量手动解析 LLM 输出的代码：

- `_extract_json()` — 从 markdown 代码块中提取 JSON
- `_fix_json_format()` — 修复格式问题
- `_fallback_parse()` — 降级解析方案

这些代码脆弱、重复，且难以维护。

### 优化方案

使用 LangChain 的 `with_structured_output` 直接绑定 Pydantic 模型，让框架处理解析：

```python
# 当前写法（脆弱）
content = self.llm.chat_simple(prompt)
json_data = self._extract_json(content)   # 各种修复逻辑
result = self._parse_llm_response(json_data)

# 优化后（稳定）
from langchain_core.language_models import BaseChatModel
llm_with_schema = llm.with_structured_output(RequirementAnalysisResult)
result = llm_with_schema.invoke(prompt)   # 直接返回 Pydantic 对象
```

### 预期收益

- 消除约 150 行重复的 JSON 解析代码
- 解析失败率大幅降低
- 代码可读性显著提升

### 涉及文件

- `core/agents/requirement_analyzer.py`
- `core/agents/test_case_generator.py`
- `core/agents/case_reviewer.py`
- `core/utils/llm_client.py`

---

## Issue 2：评审反馈注入生成器（有效迭代）

**标签**: `enhancement` `priority-high`

### 问题描述

当前评审不通过后的迭代是"盲目重试"——`generate_test_cases_node` 重新执行时完全不知道上一次哪里出了问题，导致迭代没有实际改进效果。

```python
# 当前：重新生成时没有带上评审意见
def generate_test_cases_node(state: AgentState) -> dict:
    generator = TestCaseGenerator()
    for req in requirements:
        test_cases = generator.generate(req)  # 不知道上次哪里不好
```

### 优化方案

将评审意见作为约束条件注入生成器的 prompt：

```python
def generate_test_cases_node(state: AgentState) -> dict:
    feedback = state.get("review_suggestions", [])
    review_comments = state.get("review_comments", [])
    iteration = state.get("iteration_count", 0)

    for req in requirements:
        # 第二次及以后迭代，带上上次的问题
        if iteration > 0 and feedback:
            test_cases = generator.generate(req, improvement_hints=feedback)
        else:
            test_cases = generator.generate(req)
```

同时在 `TestCaseGenerator._build_prompt()` 中增加 `improvement_hints` 参数：

```python
def _build_prompt(self, requirement: Requirement, improvement_hints: list = None) -> str:
    hint_section = ""
    if improvement_hints:
        hint_section = f"""
## 上次评审发现的问题（本次必须修复）
{chr(10).join(f'- {h}' for h in improvement_hints)}
"""
    return f"""...{hint_section}..."""
```

### 预期收益

- 迭代有实际意义，第二次生成质量明显高于第一次
- 减少无效迭代次数，节省 LLM 调用成本

### 涉及文件

- `core/agents/workflow.py` — `generate_test_cases_node`
- `core/agents/test_case_generator.py` — `_build_prompt`

---

## Issue 3：并行 Agent（需求级 fan-out）

**标签**: `enhancement` `performance` `priority-medium`

### 问题描述

当前多个需求的测试用例生成是串行的，需求越多耗时越长：

```python
# 当前：串行处理，N 个需求 = N 次串行 LLM 调用
for req in requirements:
    test_cases = generator.generate(req)
    all_test_cases.extend(test_cases)
```

### 优化方案

使用 LangGraph 的 `Send` API 实现需求级并行处理：

```python
from langgraph.constants import Send

def fan_out_requirements(state: AgentState):
    """将每个需求分发给独立的生成节点并行处理"""
    return [
        Send("generate_for_single_req", {
            "req": req,
            "feedback": state.get("review_suggestions", []),
            "iteration": state.get("iteration_count", 0)
        })
        for req in state["requirements"]
    ]

def generate_for_single_req(state: dict) -> dict:
    """单个需求的测试用例生成（并行执行）"""
    generator = TestCaseGenerator()
    test_cases = generator.generate(state["req"])
    return {"partial_test_cases": test_cases}

def fan_in_results(state: AgentState) -> dict:
    """汇总所有并行生成的结果"""
    all_cases = []
    for partial in state.get("partial_test_cases_list", []):
        all_cases.extend(partial)
    return {"test_cases": all_cases}
```

### 预期收益

- 多需求场景下执行时间从 O(n) 降为 O(1)（受限于 API 并发限制）
- 体现 LangGraph 的核心价值

### 涉及文件

- `core/agents/workflow.py` — 重构 `generate_test_cases_node`

---

## Issue 4：Tool Calling — Agent 主动获取页面信息

**标签**: `enhancement` `feature` `priority-medium`

### 问题描述

当前 Agent 生成测试用例时完全依赖需求文档的文字描述，无法感知真实页面结构，导致：

- 生成的选择器是猜测的（`input[name="email"]` 等）
- 无法发现需求文档中未提及的 UI 元素
- 测试脚本实际运行失败率高

### 优化方案

为 Agent 提供工具集，让其在生成测试用例前主动探测目标页面：

```python
from langchain_core.tools import tool

@tool
def screenshot_page(url: str) -> str:
    """截取页面截图并返回 base64，用于 AI 视觉分析页面结构"""
    # 使用 Playwright 截图
    ...

@tool
def get_page_dom(url: str) -> str:
    """获取页面的关键 DOM 结构，提取表单、按钮、输入框等元素"""
    # 使用 Playwright 获取 DOM
    ...

@tool
def search_similar_test_cases(requirement_title: str) -> str:
    """搜索历史测试用例库中相似的用例，避免重复生成"""
    # 搜索本地缓存或数据库
    ...

# 绑定工具到 LLM
llm_with_tools = llm.bind_tools([screenshot_page, get_page_dom, search_similar_test_cases])
```

### 预期收益

- 生成的测试脚本基于真实 DOM，选择器准确率大幅提升
- Agent 具备真正的"感知-决策-行动"能力
- 这是与普通 LLM 调用最大的差异化亮点

### 涉及文件

- `core/utils/tools.py` — 新建工具模块
- `core/agents/test_case_generator.py` — 集成工具调用
- `core/utils/llm_client.py` — 支持 `bind_tools`

---

## Issue 5：Human-in-the-loop（人工介入节点）

**标签**: `enhancement` `feature` `priority-medium`

### 问题描述

当前工作流是全自动的，没有任何人工介入点。在以下场景中，全自动执行存在风险：

- 评审多次不通过时，应该让人工决定是否继续
- 生成的测试脚本执行前，应该允许人工确认
- 需求分析结果有歧义时，应该让人工澄清

### 优化方案

使用 LangGraph 的 `interrupt` 机制在关键节点暂停等待人工输入：

```python
from langgraph.types import interrupt

def human_review_node(state: AgentState) -> dict:
    """人工审核节点 — 暂停等待人工决策"""
    review_score = state.get("review_score", 0)
    iteration = state.get("iteration_count", 0)

    # 展示当前状态给人工
    summary = {
        "iteration": iteration,
        "score": review_score,
        "test_cases_count": len(state.get("test_cases", [])),
        "issues": state.get("review_suggestions", [])
    }

    # 暂停，等待人工输入
    human_decision = interrupt({
        "message": "测试用例评审未通过，请决定下一步操作",
        "summary": summary,
        "options": ["continue", "skip_review", "abort"]
    })

    return {"human_decision": human_decision}

def route_after_human(state: AgentState) -> str:
    decision = state.get("human_decision", "continue")
    if decision == "abort":
        return END
    elif decision == "skip_review":
        return "generate_script"
    else:
        return "generate_test_cases"
```

### 预期收益

- 关键节点有人工把关，避免低质量用例进入执行阶段
- 体现"支持人工审核关键节点"的设计原则（项目规范要求）
- LangGraph 的核心特性之一，体现框架使用深度

### 涉及文件

- `core/agents/workflow.py` — 新增 `human_review_node`
- `main_v2.py` — 支持 checkpointer（持久化中间状态）

---

## Issue 6：Agent 记忆与历史用例复用

**标签**: `enhancement` `feature` `priority-low`

### 问题描述

每次运行工作流都是全新开始，没有利用历史执行数据：

- 相同需求重复生成，浪费 LLM 调用
- 历史测试用例中的好用例无法复用
- 无法从历史失败中学习

### 优化方案

引入 LangGraph 的 `MemorySaver` 或外部存储实现跨会话记忆：

```python
from langgraph.checkpoint.memory import MemorySaver

# 编译时注入 checkpointer
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# 运行时指定 thread_id，相同项目复用历史状态
config = {"configurable": {"thread_id": "project-login-feature"}}
result = app.invoke(initial_state, config=config)
```

同时建立本地测试用例缓存，避免重复生成：

```python
# 基于需求内容的哈希缓存
cache_key = hashlib.md5(requirement_text.encode()).hexdigest()
if cache.exists(cache_key):
    return cache.get(cache_key)
```

### 预期收益

- 相同需求直接复用缓存，响应速度提升 10x
- 支持断点续跑，中途失败不需要从头开始
- 为后续引入数据库（PostgreSQL）打基础

### 涉及文件

- `core/utils/cache.py` — 新建缓存模块
- `core/agents/workflow.py` — 集成 checkpointer
- `main_v2.py` — 传入 thread_id

---

---

## Issue 7：LLMClient 缺少重试机制和 Token 成本追踪

**标签**: `enhancement` `reliability` `priority-high`

### 问题描述

当前 `LLMClient.chat()` 直接调用 `self._llm.invoke()`，没有任何容错处理：

- 网络抖动或 API 限流时直接抛出异常，整个工作流中断
- 没有记录每次调用的 Token 消耗，无法统计成本
- 每次调用都创建新的 `LLMClient` 实例（各 Agent 的 `__init__` 都调用 `get_llm_client()`），浪费资源

### 优化方案

**1. 加入指数退避重试：**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
)
def chat(self, messages, ...):
    ...
```

**2. Token 成本追踪：**

```python
class TokenTracker:
    """全局 Token 使用统计"""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    def record(self, usage: TokenUsage):
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens

    @property
    def estimated_cost_usd(self) -> float:
        # 按模型单价计算
        ...
```

**3. 单例 LLMClient：**

```python
_client_instance = None

def get_llm_client() -> LLMClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
```

### 涉及文件

- `core/utils/llm_client.py`

---

## Issue 8：MidsceneScriptGenerator 的 action 转换逻辑脆弱

**标签**: `bug` `enhancement` `priority-high`

### 问题描述

`_convert_action_to_ai_prompt()` 和 `_convert_expected_to_ai_prompt()` 用大量 `if "关键词" in action` 的字符串匹配来转换测试步骤，这是整个项目最脆弱的部分：

```python
# 当前：硬编码关键词匹配，极易失效
if "输入" in action or "填写" in action:
    if "邮箱" in action or "用户名" in action:
        return f'在邮箱或用户名输入框中输入 "{data}"'
    elif "密码" in action:
        return f'在密码输入框中输入 "{data}"'
    elif "搜索" in action or "关键词" in action:
        ...
# 遇到"请在搜索栏键入内容"这类描述就完全失效
```

而且 `_generate_decorators()` 方法生成的是 Python pytest 装饰器，但脚本是 TypeScript，这个方法根本没被调用，是死代码。

### 优化方案

**方案 A（短期）**：把 action 转换也交给 LLM 处理，而不是规则匹配：

```python
def _convert_action_to_ai_prompt(self, action: str, data: str) -> str:
    """用 LLM 将测试步骤转换为 Midscene 自然语言指令"""
    # 对于简单操作，LLM 一次调用可以批量转换所有步骤
    # 避免每个步骤单独调用
    ...
```

**方案 B（长期，配合 Issue #4）**：结合 Tool Calling，让 Agent 在生成脚本时直接感知页面 DOM，生成精确的选择器而不是自然语言描述。

同时清理死代码 `_generate_decorators()`。

### 涉及文件

- `core/automation/midscene_generator.py`

---

## Issue 9：TestExecutor 输出解析用正则匹配，不稳定

**标签**: `bug` `reliability` `priority-medium`

### 问题描述

`parse_playwright_output()` 用正则表达式解析 Playwright CLI 的文本输出来统计测试结果，这非常脆弱：

- Playwright 版本升级后输出格式变化会导致解析失败
- 文件中有两段重复的汇总解析代码（第二段是死代码，`return` 之后的代码永远不会执行）
- 中文路径、特殊字符可能导致正则匹配失败

```python
# 当前：解析文本输出，脆弱
summary_passed = re.search(r"(\d+)\s+passed", output)

# 文件中存在死代码（return 之后还有代码）
results["total"] = results["passed"] + results["failed"] + results["skipped"]
return results  # ← 这里已经 return 了

# 下面这段永远不会执行
summary_passed = re.search(r"(\d+)\s+passed", output)  # 死代码
```

### 优化方案

使用 Playwright 的 JSON reporter 替代文本解析：

```python
# 让 Playwright 输出 JSON 格式结果
cmd = ["npx", "playwright", "test", script_path,
       "--reporter=json",           # 输出 JSON
       f"--output={json_output_path}"]

# 直接解析 JSON，稳定可靠
with open(json_output_path) as f:
    report = json.load(f)
    passed = report["stats"]["expected"]
    failed = report["stats"]["unexpected"]
```

同时清理死代码。

### 涉及文件

- `core/automation/test_executor.py`

---

## Issue 10：工作流缺少可观测性（Tracing）

**标签**: `enhancement` `observability` `priority-medium`

### 问题描述

当前工作流的执行过程只有 `print()` 输出，无法：

- 追踪每个 Agent 节点的输入/输出
- 统计各节点耗时
- 在出错时快速定位是哪个节点、哪次 LLM 调用出了问题
- 对比不同迭代之间的差异

### 优化方案

**方案 A：集成 LangSmith（LangChain 官方追踪）**

```python
# 只需设置环境变量，自动追踪所有 LangChain 调用
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-key"
os.environ["LANGCHAIN_PROJECT"] = "ai-test-platform"
```

**方案 B：轻量级本地追踪（不依赖外部服务）**

```python
import time
from functools import wraps

def trace_node(node_name: str):
    """节点追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(state):
            start = time.time()
            print(f"[TRACE] → {node_name} 开始")
            result = func(state)
            elapsed = time.time() - start
            print(f"[TRACE] ← {node_name} 完成 ({elapsed:.2f}s)")
            # 写入追踪日志
            _write_trace_log(node_name, state, result, elapsed)
            return result
        return wrapper
    return decorator

@trace_node("analyze_requirements")
def analyze_requirements_node(state):
    ...
```

### 涉及文件

- `core/agents/workflow.py`
- `core/utils/llm_client.py`
- `.env.example` — 新增 LangSmith 配置项

---

## Issue 11：main_v2.py 硬编码需求文件和 URL

**标签**: `enhancement` `usability` `priority-low`

### 问题描述

`main_v2.py` 中需求文件路径和目标 URL 是硬编码的：

```python
# 当前：硬编码，每次换需求都要改代码
requirement_file = "examples/requirement_baidu.md"
final_state = run_workflow(
    requirement_text=requirement_text,
    page_url="https://www.baidu.com"  # 可根据实际项目修改
)
```

### 优化方案

支持命令行参数和配置文件两种方式：

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="AI 测试自动化平台")
    parser.add_argument("--requirement", "-r",
                        default="examples/requirement_baidu.md",
                        help="需求文档路径")
    parser.add_argument("--url", "-u",
                        default="https://www.baidu.com",
                        help="目标页面 URL")
    parser.add_argument("--max-iterations", "-i",
                        type=int, default=2,
                        help="最大迭代次数")
    parser.add_argument("--no-execute", action="store_true",
                        help="只生成用例，不执行测试")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
```

使用方式：
```bash
python main_v2.py --requirement examples/requirement_login.md --url https://example.com/login
python main_v2.py -r docs/req.md -u https://app.com --no-execute
```

### 涉及文件

- `main_v2.py`

---

## Issue 12：代理设置清除代码散落各处

**标签**: `tech-debt` `priority-low`

### 问题描述

清除代理环境变量的代码在多个文件中重复出现：

```python
# 以下代码出现在：
# - main_v2.py
# - core/agents/workflow.py
# - core/automation/test_executor.py
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(var, None)
os.environ['NO_PROXY'] = '*'
```

### 优化方案

统一到 `core/utils/env_setup.py`，在 `main_v2.py` 入口处调用一次：

```python
# core/utils/env_setup.py
def disable_proxy():
    """禁用系统代理，解决国内环境连接问题"""
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        os.environ.pop(var, None)
    os.environ['NO_PROXY'] = '*'

# main_v2.py — 只在入口调用一次
from core.utils.env_setup import disable_proxy
disable_proxy()
```

### 涉及文件

- `main_v2.py`
- `core/agents/workflow.py`
- `core/automation/test_executor.py`
- `core/utils/env_setup.py` — 新建

---

## 优先级汇总

| Issue | 标题 | 难度 | 亮点 | 优先级 |
|-------|------|------|------|--------|
| #1 | 结构化输出替换手动 JSON 解析 | 低 | 中 | P0 |
| #2 | 评审反馈注入生成器 | 低 | 高 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 低 | 中 | P0 |
| #8 | MidsceneScriptGenerator action 转换 | 中 | 高 | P0 |
| #9 | TestExecutor 输出解析改用 JSON reporter | 低 | 中 | P0 |
| #3 | 并行 Agent（fan-out） | 中 | 高 | P1 |
| #4 | Tool Calling | 高 | 非常高 | P1 |
| #5 | Human-in-the-loop | 中 | 高 | P1 |
| #10 | 工作流可观测性（Tracing） | 中 | 高 | P1 |
| #6 | Agent 记忆与历史用例复用 | 中 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 低 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 低 | 低 | P2 |

---

## Issue 13：requirement_analyzer_v2.py 是废弃文件，导入路径已损坏

**标签**: `bug` `tech-debt` `priority-high`

### 问题描述

`core/agents/requirement_analyzer_v2.py` 是一个遗留文件，存在严重问题：

```python
# 错误的导入路径（缺少 core. 前缀，运行时直接报 ModuleNotFoundError）
from models.requirement import Requirement, RequirementAnalysisResult  # ❌
from models.config import get_settings                                  # ❌

# 正确应该是
from core.models.requirement import ...
from core.models.config import ...
```

同时它使用了已废弃的 Pydantic V1 API：
```python
print(result.json(ensure_ascii=False, indent=2))  # ❌ Pydantic V2 已移除 .json()
# 应该是
print(result.model_dump_json(indent=2))
```

而且 `requirement_analyzer.py` 已经是完整的 Pydantic 版本，这个 v2 文件完全是重复代码。

### 优化方案

直接删除 `requirement_analyzer_v2.py`，它的功能已经被 `requirement_analyzer.py` 完全覆盖。

### 涉及文件

- `core/agents/requirement_analyzer_v2.py` — 删除

---

## Issue 14：Requirement ID 格式限制过严，超过 999 个需求就崩溃

**标签**: `bug` `priority-medium`

### 问题描述

`Requirement` 和 `TestCase` 的 ID 格式用正则强制限制为 3 位数字：

```python
# core/models/requirement.py
id: str = Field(pattern=r"^REQ_\d{3}$")  # 只允许 REQ_001 ~ REQ_999

# core/models/test_case.py
id: str = Field(pattern=r"^TC_\d{3}$")   # 只允许 TC_001 ~ TC_999
```

当需求超过 999 个，或者 LLM 生成了 `REQ_0001`（4位）这样的 ID 时，Pydantic 验证直接失败，触发降级逻辑。

实际上 LLM 有时会生成 `TC_001_001`（子用例）这样的格式，也会被拒绝。

### 优化方案

放宽正则，支持更多位数：

```python
# 支持 1-6 位数字，兼容子用例格式
id: str = Field(pattern=r"^REQ_\d{1,6}$")
id: str = Field(pattern=r"^TC_[\d_]{1,10}$")  # 支持 TC_001_001 格式
```

### 涉及文件

- `core/models/requirement.py`
- `core/models/test_case.py`

---

## Issue 15：TestCase.title 禁止以数字开头，但 LLM 经常生成这样的标题

**标签**: `bug` `priority-medium`

### 问题描述

`TestCase` 的 title 验证器禁止标题以数字开头：

```python
@field_validator('title')
@classmethod
def validate_title_format(cls, v):
    if v[0].isdigit():
        raise ValueError("测试用例标题不能以数字开头")
```

但 LLM 生成的标题经常是 `"1. 验证用户登录成功"` 或 `"TC001 正常登录流程"` 这样的格式，导致验证失败触发降级，生成质量下降。

这个限制没有实际业务意义。

### 优化方案

移除这个不合理的限制，只保留真正有意义的验证（长度、特殊字符）：

```python
@field_validator('title')
@classmethod
def validate_title_format(cls, v):
    v = v.strip()
    # 只过滤真正有问题的字符（文件系统不允许的）
    invalid_chars = ['<', '>', '|', '*', '?', '"', '\n', '\r']
    for char in invalid_chars:
        if char in v:
            raise ValueError(f"标题不能包含字符: {char}")
    return v
```

### 涉及文件

- `core/models/test_case.py`

---

## Issue 16：config.yaml 与 ProjectSettings 双重配置，实际只用了一个

**标签**: `tech-debt` `priority-medium`

### 问题描述

项目有两套配置系统：

1. `config/config.yaml` — YAML 文件配置
2. `core/models/config.py` 的 `ProjectSettings` — 从 `.env` 读取

但实际代码中**只使用了 `ProjectSettings`**，`config.yaml` 从未被读取（没有任何代码 `import` 或 `open` 它）。这造成了混乱：

- 新人看到 `config.yaml` 会以为修改它有效，实际无效
- `config.yaml` 中的 `llm.temperature: 0.7` 和 `ProjectSettings` 中的 `llm_temperature: float = Field(default=0.7)` 是两份独立的默认值

### 优化方案

二选一：

**方案 A（推荐）**：删除 `config.yaml`，在 `ProjectSettings` 中补充注释说明每个配置项的含义，`.env.example` 作为唯一配置参考。

**方案 B**：让 `ProjectSettings` 支持从 `config.yaml` 读取默认值，`.env` 只覆盖敏感信息（API Key）：

```python
import yaml

class ProjectSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        yaml_file="config/config.yaml",  # pydantic-settings 支持 yaml
    )
```

### 涉及文件

- `config/config.yaml`
- `core/models/config.py`

---

## Issue 17：playwright.config.ts 有重复字段和错误的 baseURL

**标签**: `bug` `priority-medium`

### 问题描述

`config/playwright.config.ts` 有两个问题：

**1. `outputFolder` 字段重复定义：**
```typescript
reporter: [
  ['allure-playwright', { 
    outputFolder: 'allure-results',   // 第一次
    suiteTitle: false,
    detail: true,
    outputFolder: './allure-results'  // 第二次，覆盖了第一次 ❌
  }]
],
```

**2. `baseURL` 硬编码为 `localhost:3000`，但测试的是百度等外部网站：**
```typescript
use: {
  baseURL: 'http://localhost:3000',  // ❌ 测试百度时完全用不到
}
```

### 优化方案

```typescript
reporter: [
  ['allure-playwright', { 
    outputFolder: './allure-results',  // 只保留一个，用相对路径
    suiteTitle: false,
    detail: true,
  }]
],
use: {
  baseURL: process.env.TEST_BASE_URL || 'https://example.com',  // 从环境变量读取
}
```

### 涉及文件

- `config/playwright.config.ts`

---

## Issue 18：markdown_parser.py 过于简单，无法处理复杂需求文档

**标签**: `enhancement` `priority-medium`

### 问题描述

当前的 `parse_markdown()` 只是简单地 `open` + `read`，完全没有解析：

```python
def parse_markdown(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content  # 直接返回原始文本
```

`extract_sections()` 函数只处理一级标题（`# `），遇到二级标题（`## `）就会出错，而且这个函数在整个项目中从未被调用过（死代码）。

实际问题：
- 不支持 PDF、Word 格式（`config.yaml` 里提到了支持，但没实现）
- 不能提取结构化信息（表格、列表、代码块）
- 大型需求文档直接全文传给 LLM，Token 浪费严重

### 优化方案

**短期**：改进 `extract_sections()` 支持多级标题，并在 `RequirementAnalyzer` 中实际使用它做预处理：

```python
def extract_sections(content: str, max_level: int = 3) -> Dict[str, str]:
    """提取多级标题章节"""
    sections = {}
    # 支持 #, ##, ### 等多级标题
    pattern = re.compile(r'^(#{1,' + str(max_level) + r'})\s+(.+)$', re.MULTILINE)
    ...
```

**长期**：支持多格式文档：

```python
class DocumentParser:
    def parse(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix == '.md':
            return self._parse_markdown(file_path)
        elif suffix == '.pdf':
            return self._parse_pdf(file_path)      # PyMuPDF
        elif suffix in ('.docx', '.doc'):
            return self._parse_word(file_path)     # python-docx
        elif suffix == '.txt':
            return self._parse_text(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")
```

### 涉及文件

- `core/parsers/markdown_parser.py`
- `core/parsers/__init__.py`

---

## Issue 19：AgentState 使用 TypedDict，无法享受 Pydantic 验证

**标签**: `enhancement` `priority-medium`

### 问题描述

`workflow.py` 的 `AgentState` 用 `TypedDict` 定义，而项目其他地方都在用 Pydantic：

```python
class AgentState(TypedDict):
    requirement_text: str
    requirements: Optional[List[dict]]   # ← 用 dict 而不是 Requirement 模型
    test_cases: Optional[List[dict]]     # ← 同上
    review_score: Optional[float]
    ...
```

问题：
- `requirements` 和 `test_cases` 存的是 `dict`，但 Agent 内部用的是 Pydantic 模型，存取时需要反复 `model_dump()` / `model_validate()`
- `TypedDict` 没有运行时验证，字段类型错误只能在运行时发现
- `iteration_count` 没有默认值，初始化时必须手动设为 0，容易遗漏

### 优化方案

LangGraph 支持 Pydantic 模型作为 State：

```python
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """Agent 共享状态 - Pydantic 版本"""
    requirement_text: str
    requirements: List[Requirement] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    review_passed: bool = False
    review_score: float = 0.0
    review_comments: List[ReviewComment] = Field(default_factory=list)
    review_suggestions: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 2
    ...
```

这样 Agent 节点可以直接操作 Pydantic 对象，不需要反复转换。

### 涉及文件

- `core/agents/workflow.py`

---

## Issue 20：缺少单元测试，核心逻辑无法验证

**标签**: `enhancement` `testing` `priority-high`

### 问题描述

项目 `tests/` 目录结构存在但几乎没有实际测试：

- `tests/unit/` — 目录存在，内容未知
- `tests/integration/` — 目录存在，内容未知
- 核心 Agent 逻辑（JSON 解析、Pydantic 验证、路由逻辑）完全没有测试覆盖

每次修改 Agent 代码都需要跑完整流程（调用 LLM）才能验证，成本高、速度慢。

### 优化方案

为核心逻辑添加不依赖 LLM 的单元测试：

```python
# tests/unit/test_requirement_analyzer.py
import pytest
from unittest.mock import patch, MagicMock
from core.agents.requirement_analyzer import RequirementAnalyzer

class TestRequirementAnalyzer:

    def test_extract_json_from_markdown_block(self):
        """测试从 markdown 代码块提取 JSON"""
        analyzer = RequirementAnalyzer()
        content = '```json\n{"key": "value"}\n```'
        result = analyzer._extract_json(content)
        assert result == {"key": "value"}

    def test_fix_json_format_with_prefix(self):
        """测试修复带前缀的 JSON"""
        analyzer = RequirementAnalyzer()
        content = 'json\n{"key": "value"}'
        result = analyzer._fix_json_format(content)
        assert result.startswith('{')

    @patch('core.agents.requirement_analyzer.get_llm_client')
    def test_analyze_with_mock_llm(self, mock_llm_factory):
        """用 Mock LLM 测试完整分析流程"""
        mock_llm = MagicMock()
        mock_llm.chat_simple.return_value = '''
        {"requirements": [{"id": "REQ_001", "title": "登录功能",
          "description": "用户可以登录系统", "priority": "high",
          "type": "functional", "acceptance_criteria": ["登录成功跳转首页"],
          "ui_elements": ["邮箱输入框"]}],
         "summary": "登录功能需求", "total_count": 1}
        '''
        mock_llm_factory.return_value = mock_llm

        analyzer = RequirementAnalyzer()
        result = analyzer.analyze("用户登录功能需求文档")
        assert len(result["requirements"]) == 1
```

### 涉及文件

- `tests/unit/test_requirement_analyzer.py` — 新建
- `tests/unit/test_test_case_generator.py` — 新建
- `tests/unit/test_workflow_routing.py` — 新建
- `tests/unit/test_models.py` — 新建

---

## Issue 21：缺少日志系统，全靠 print()

**标签**: `enhancement` `observability` `priority-medium`

### 问题描述

整个项目用 `print()` 输出信息，没有正式的日志系统：

- 无法按级别过滤（DEBUG/INFO/WARNING/ERROR）
- 无法写入文件持久化
- 无法在生产环境关闭调试输出
- `[DEBUG]` 标记的调试信息和正常输出混在一起

`LogConfig` 模型已经在 `config.py` 中定义好了，但从未被使用。

### 优化方案

在项目入口初始化标准 logging，替换所有 `print()`：

```python
# core/utils/logger.py
import logging
import logging.handlers
from core.models.config import get_settings

def setup_logging():
    settings = get_settings()
    log_config = settings.get_log_config()

    logging.basicConfig(
        level=getattr(logging, log_config.level),
        format=log_config.format,
        handlers=[
            logging.StreamHandler(),
            *([ logging.handlers.RotatingFileHandler(
                    log_config.file,
                    maxBytes=log_config.max_size * 1024 * 1024,
                    backupCount=log_config.backup_count
                )] if log_config.file else [])
        ]
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# 各模块使用
logger = get_logger(__name__)
logger.info("[Agent] 需求分析中...")
logger.debug(f"[DEBUG] 脚本路径: {script_path}")
logger.error(f"[ERROR] LLM 评审失败: {e}")
```

### 涉及文件

- `core/utils/logger.py` — 新建
- 所有 Agent 和 automation 模块 — 替换 `print()`

---

## Issue 22：AllureReporter.open_report() 启动 HTTP 服务后进程泄漏

**标签**: `bug` `priority-low`

### 问题描述

`open_report()` 用 `subprocess.Popen` 启动了一个 Python HTTP 服务进程，但：

- 进程 PID 虽然返回了，但没有任何机制在程序退出时关闭它
- 每次运行 `main_v2.py` 都会启动一个新的 HTTP 服务，端口随机，旧进程一直占用内存
- Windows 上 `DETACHED_PROCESS` 标志让进程完全脱离父进程，无法被 Python 的 `atexit` 清理

### 优化方案

**方案 A**：改用 `allure open` 命令（会自动管理进程生命周期）：

```python
# allure open 会自动打开浏览器并在关闭时退出
subprocess.run(["allure", "open", str(self.report_dir)])
```

**方案 B**：注册 `atexit` 清理函数：

```python
import atexit

def open_report(self):
    process = subprocess.Popen(...)
    atexit.register(process.terminate)  # 程序退出时自动终止
    return {"pid": process.pid, ...}
```

**方案 C（最简单）**：直接用 `webbrowser` 打开已生成的静态 HTML 文件，不需要 HTTP 服务：

```python
import webbrowser
index_file = self.report_dir / "index.html"
webbrowser.open(f"file:///{index_file.absolute()}")
```

### 涉及文件

- `core/automation/allure_reporter.py`

---

## Issue 23：需求文档示例太简单，无法测试复杂场景

**标签**: `enhancement` `priority-low`

### 问题描述

`examples/` 目录只有两个极简的需求文档：

- `requirement_login.md` — 登录功能，约 30 行
- `requirement_baidu.md` — 百度搜索，约 20 行

这两个文档太简单，无法暴露以下问题：
- 多需求文档（10+ 个需求）时的并行性能
- 需求之间有依赖关系时的处理
- 包含表格、图片引用、代码块的复杂 Markdown
- 非功能性需求（性能、安全）的处理

### 优化方案

补充更丰富的示例文档：

```
examples/
├── requirement_login.md          # 现有：简单登录
├── requirement_baidu.md          # 现有：简单搜索
├── requirement_ecommerce.md      # 新增：电商购物车（多需求、有依赖）
├── requirement_complex.md        # 新增：包含表格、非功能需求
└── requirement_api.md            # 新增：API 接口测试需求
```

### 涉及文件

- `examples/` — 新增示例文件

---

## 优先级汇总（完整版）

| Issue | 标题 | 类型 | 难度 | 优先级 |
|-------|------|------|------|--------|
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | 低 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | 低 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | 低 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | 中 | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | 低 | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | 低 | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | 低 | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | 低 | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | 中 | P1 |
| #4 | Tool Calling | 功能 | 高 | P1 |
| #5 | Human-in-the-loop | 功能 | 中 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | 中 | P1 |
| #14 | ID 格式正则限制过严 | Bug | 低 | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | 低 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | 中 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | 中 | P1 |
| #20 | 缺少单元测试 | 测试 | 中 | P1 |
| #21 | 缺少日志系统 | 可观测性 | 低 | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | 低 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | 低 | P2 |
| #23 | 需求文档示例太简单 | 文档 | 低 | P2 |

---

## Issue 24：requirements.txt 缺少关键依赖，且版本固定策略不一致

**标签**: `bug` `dependency` `priority-high`

### 问题描述

`requirements.txt` 存在多个问题：

**1. 缺少已使用的依赖：**
```
# 代码中已使用但未列出
langgraph          # workflow.py 中 from langgraph.graph import StateGraph
pydantic-settings  # config.py 中 from pydantic_settings import BaseSettings
tenacity           # 重试机制（计划中）
httpx              # llm_client.py 中 import httpx
```

**2. 列出了未使用的依赖：**
```
PyMuPDF==1.24.0    # 代码中从未 import，markdown_parser.py 只用了内置 open()
python-docx==1.1.0 # 同上，从未使用
markdown==3.7      # 同上，从未使用
```

**3. 版本固定过死，升级困难：**
```
openai==1.12.0     # 固定到小版本，安全补丁无法自动获取
langchain==0.3.13  # 同上
```

### 优化方案

```
# requirements.txt（修正版）

# LLM 和 Agent
openai>=1.12.0,<2.0.0
langchain>=0.3.13,<0.4.0
langchain-core>=0.3.28,<0.4.0
langchain-openai>=0.2.14,<0.3.0
langgraph>=0.2.0,<0.3.0          # 补充缺失

# 数据验证
pydantic>=2.10.3,<3.0.0
pydantic-settings>=2.0.0,<3.0.0  # 补充缺失

# HTTP 客户端
httpx>=0.27.0,<1.0.0              # 补充缺失

# 文档解析（按需安装）
PyMuPDF>=1.24.0                   # 仅在需要 PDF 解析时
python-docx>=1.1.0                # 仅在需要 Word 解析时

# UI 自动化
playwright>=1.48.0,<2.0.0
pytest-playwright>=0.5.2

# 测试框架
pytest>=8.3.4
pytest-asyncio>=0.24.0
allure-pytest>=2.13.5

# 工具
python-dotenv>=1.0.1
pyyaml>=6.0.2
```

### 涉及文件

- `requirements.txt`

---

## Issue 25：main.py（阶段1）与 main_v2.py（阶段2）并存，职责不清

**标签**: `tech-debt` `priority-medium`

### 问题描述

项目根目录有两个入口文件：

- `main.py` — 阶段1，直接调用 Agent，无 LangGraph
- `main_v2.py` — 阶段2，使用 LangGraph 工作流

两个文件有大量重复代码（`clean_history_data()`、`save_results()` 等函数几乎一模一样），而且 `main.py` 已经过时，README 也说"推荐使用 main_v2.py"。

但 `main.py` 仍然存在，新人不知道该用哪个，而且两个文件的重复代码会导致维护时只改了一处。

### 优化方案

**方案 A**：删除 `main.py`，将阶段1的功能作为 `main_v2.py` 的 `--simple` 模式：
```bash
python main_v2.py --simple   # 阶段1模式，不用 LangGraph
python main_v2.py            # 阶段2模式（默认）
```

**方案 B**：保留 `main.py` 但重命名为 `main_v1.py`，并在文件顶部加明显的废弃注释：
```python
# ⚠️ 已废弃：请使用 main_v2.py
# 此文件仅作为阶段1的历史参考
```

同时将公共函数（`clean_history_data` 等）提取到 `core/utils/runner.py`。

### 涉及文件

- `main.py`
- `main_v2.py`
- `core/utils/runner.py` — 新建（提取公共逻辑）

---

## Issue 26：generate_allure_from_results.py 硬编码了错误信息和测试名称

**标签**: `bug` `priority-medium`

### 问题描述

`scripts/generate_allure_from_results.py` 是一个降级脚本，但它有严重的硬编码问题：

```python
# 硬编码的错误信息（来自某次具体的运行）
error_message = "failed to call AI model service: 400 Access denied, please make sure your account is in good standing"

# 硬编码的默认测试名称（百度搜索相关）
if not failed_tests:
    failed_tests = [
        "TC_001: 验证使用有效关键词进行搜索并成功跳转",
        "TC_002: 验证搜索框为空时点击搜索按钮的处理",
        "TC_003: 验证搜索特殊字符关键词"
    ]

# 硬编码的执行时间
duration=2.5 + i * 0.2  # 模拟不同的执行时间
```

这意味着无论实际运行什么测试，降级报告永远显示"百度搜索"的测试名称和同一个错误信息。

### 优化方案

从 `output/test_cases*.json` 读取实际的测试用例名称，从 `output/execution*.json` 读取实际的错误信息：

```python
# 从测试用例文件读取实际名称
test_cases_files = list(output_dir.glob("test_cases*.json"))
if test_cases_files:
    with open(max(test_cases_files, key=lambda p: p.stat().st_mtime)) as f:
        data = json.load(f)
        failed_tests = [f"{tc['id']}: {tc['title']}" for tc in data.get("test_cases", [])]

# 从执行结果读取实际错误信息
error_message = execution_data.get("error") or execution_data.get("stderr", "测试执行失败")
```

### 涉及文件

- `scripts/generate_allure_from_results.py`

---

## Issue 27：conftest.py 中 OUTPUT_DIR 被重复定义，覆盖了导入的值

**标签**: `bug` `priority-medium`

### 问题描述

`tests/conftest.py` 中存在变量遮蔽（shadowing）问题：

```python
# 第1行：从 project_paths 导入
from core.utils.project_paths import OUTPUT_DIR, GENERATED_TESTS_DIR

# 第N行：又重新赋值，覆盖了导入的值！
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR          # ← 用绝对路径覆盖了相对路径
GENERATED_TESTS_DIR = PROJECT_ROOT / GENERATED_TESTS_DIR  # ← 同上
```

这会导致：
- `project_paths.py` 中的路径是相对路径（`Path("output")`）
- `conftest.py` 中变成了绝对路径（`/path/to/project/output`）
- 两处路径不一致，可能导致清理操作作用在错误的目录

### 优化方案

在 `project_paths.py` 中统一提供绝对路径版本：

```python
# core/utils/project_paths.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent  # 项目根目录

OUTPUT_DIR = PROJECT_ROOT / "output"
GENERATED_TESTS_DIR = PROJECT_ROOT / "midscene_run" / "generated"
# ...
```

然后 `conftest.py` 直接使用，不再重新赋值：
```python
from core.utils.project_paths import OUTPUT_DIR, GENERATED_TESTS_DIR
# 不需要再做 PROJECT_ROOT / OUTPUT_DIR 的操作
```

### 涉及文件

- `tests/conftest.py`
- `core/utils/project_paths.py`

---

## Issue 28：package.json 和 playwright.config.ts 放在 config/ 子目录，导致 npx 命令找不到配置

**标签**: `bug` `priority-high`

### 问题描述

`package.json` 和 `playwright.config.ts` 都放在 `config/` 子目录下，但 `TestExecutor` 在项目根目录执行 `npx playwright test`：

```python
# test_executor.py
result = subprocess.run(
    ["npx", "playwright", "test", script_path, ...],
    # 没有指定 cwd，默认在项目根目录执行
)
```

Playwright 默认在当前目录查找 `playwright.config.ts`，但配置文件在 `config/playwright.config.ts`，所以：
- 要么 Playwright 找不到配置文件，使用默认配置
- 要么需要每次都加 `--config config/playwright.config.ts` 参数

`package.json` 在 `config/` 目录也意味着 `node_modules` 会安装在 `config/node_modules/`，而不是项目根目录，导致 `npx` 找不到 `@midscene/web` 等包。

### 优化方案

将 `package.json`、`playwright.config.ts`、`tsconfig.json` 移到项目根目录（标准做法）：

```
项目根目录/
├── package.json           # 移到根目录
├── playwright.config.ts   # 移到根目录
├── tsconfig.json          # 移到根目录
├── node_modules/          # npm install 后在根目录
├── config/
│   ├── config.yaml        # 只保留 Python 配置
│   └── pytest.ini
```

同时在 `TestExecutor` 中明确指定配置文件路径：
```python
parts = ["npx", "playwright", "test", script_path,
         "--config", "playwright.config.ts", ...]
```

### 涉及文件

- `config/package.json` → 移到根目录
- `config/playwright.config.ts` → 移到根目录
- `config/tsconfig.json` → 移到根目录
- `core/automation/test_executor.py` — 更新配置文件路径

---

## Issue 29：README.md 中的环境变量说明与实际不符

**标签**: `documentation` `priority-low`

### 问题描述

`README.md` 中的配置说明有错误：

```markdown
# README.md 中写的
# ANTHROPIC_API_KEY=your_api_key_here  ← 错误！项目用的是 LLM_KEY

# 实际 .env.example 中的
LLM_KEY=your_api_key_here
```

README 还提到"支持OpenAI、阿里云百炼、智谱AI等"，但 `LLMConfig.validate_model()` 的已知模型列表里没有智谱AI的模型名称。

另外 README 的虚拟环境激活命令写的是 `venv\Scripts\activate`，但项目实际使用的是 `.venv`（所有文档和 skill 里都是 `.venv\Scripts\activate`）。

### 优化方案

统一更新 README：
- 修正环境变量名称
- 统一虚拟环境目录名（`.venv`）
- 补充智谱AI的模型名称到支持列表

### 涉及文件

- `README.md`

---

## Issue 30：tests/midscene.config.ts 放错了目录，且与 config/ 下的配置重复

**标签**: `tech-debt` `priority-low`

### 问题描述

`tests/midscene.config.ts` 放在 `tests/` 目录下，但它是 Midscene 的全局配置，不是测试文件：

```typescript
// tests/midscene.config.ts
export const midsceneConfig = {
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
  modelName: process.env.MIDSCENE_MODEL_NAME || 'gpt-4o',
};
```

同时 `core/models/config.py` 的 `ProjectSettings` 里也有 Midscene 相关配置：
```python
openai_api_key: Optional[str] = ...
openai_base_url: Optional[str] = ...
midscene_model_name: Optional[str] = ...
```

两套配置并存，实际生效的是哪个不清楚。

### 优化方案

删除 `tests/midscene.config.ts`，Midscene 的配置统一通过 `.env` 文件的环境变量管理（Midscene 本身支持直接读取 `OPENAI_API_KEY` 等环境变量，不需要额外的配置文件）。

### 涉及文件

- `tests/midscene.config.ts` — 删除
- `core/models/config.py` — 保留，作为唯一配置来源

---

## Issue 31：temp/ 目录和调试文件被提交到仓库

**标签**: `tech-debt` `priority-low`

### 问题描述

项目根目录有一个 `temp/` 目录，里面有调试文件：
```
temp/debug_output.txt
```

`output/playwright_debug.txt` 也是调试产物，不应该被提交。

`.gitignore` 没有忽略这些目录：
```gitignore
# 当前 .gitignore 缺少
temp/
output/
```

### 优化方案

更新 `.gitignore`：
```gitignore
# 运行时产物
temp/
output/
midscene_run/generated/
midscene_run/cache/
```

同时删除已提交的调试文件。

### 涉及文件

- `.gitignore`
- `temp/` — 删除目录
- `output/playwright_debug.txt` — 删除

---

## Issue 32：pytest.ini 的 testpaths 配置与实际测试目录不匹配

**标签**: `bug` `priority-medium`

### 问题描述

`config/pytest.ini` 中：

```ini
[pytest]
testpaths = tests   # 指向 tests/ 目录
```

但 `tests/unit/` 和 `tests/integration/` 目录是空的（没有任何测试文件），而生成的测试脚本在 `midscene_run/generated/`（TypeScript 文件，pytest 无法执行）。

同时 `pytest.ini` 放在 `config/` 子目录，但 pytest 默认在项目根目录查找 `pytest.ini`，需要每次用 `-c config/pytest.ini` 指定，否则配置不生效。

### 优化方案

将 `pytest.ini` 移到项目根目录，并更新 `testpaths`：

```ini
[pytest]
testpaths = tests/unit tests/integration
asyncio_mode = auto
```

### 涉及文件

- `config/pytest.ini` → 移到根目录

---

## Issue 33：workflow.py 中 optimize_test_cases_node 节点定义了但从未加入图

**标签**: `bug` `tech-debt` `priority-low`

### 问题描述

`workflow.py` 中定义了 `optimize_test_cases_node` 函数，但在 `build_workflow()` 中从未被添加到图中：

```python
# 定义了节点函数
def optimize_test_cases_node(state: AgentState) -> dict:
    """优化测试用例"""
    test_cases = state["test_cases"]
    optimized = []
    for tc in test_cases:
        if "priority" not in tc:
            tc["priority"] = "medium"
        optimized.append(tc)
    return {"test_cases": optimized}

# build_workflow() 中从未调用
workflow.add_node("analyze_requirements", analyze_requirements_node)
workflow.add_node("generate_test_cases", generate_test_cases_node)
workflow.add_node("review_test_cases", review_test_cases_node)
# optimize_test_cases_node 从未被 add_node ← 死代码
```

### 优化方案

二选一：
- 如果有用：在评审通过后、脚本生成前加入图中
- 如果没用：直接删除

### 涉及文件

- `core/agents/workflow.py`

---

## Issue 34：缺少 CI/CD 配置，无法自动化验证

**标签**: `enhancement` `priority-low`

### 问题描述

项目没有任何 CI/CD 配置（GitHub Actions、GitLab CI 等），导致：
- 每次提交无法自动运行单元测试
- 依赖安装是否正常无法自动验证
- 代码质量检查（lint、type check）需要手动执行

### 优化方案

添加 GitHub Actions 基础工作流：

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: python -m pytest tests/unit/ -v
      - name: Type check
        run: mypy core/ --ignore-missing-imports
      - name: Lint
        run: ruff check core/
```

### 涉及文件

- `.github/workflows/ci.yml` — 新建

---

## Issue 35：缺少类型检查配置（mypy/pyright）

**标签**: `enhancement` `code-quality` `priority-low`

### 问题描述

项目使用了大量类型注解和 Pydantic，但没有配置静态类型检查工具。现有代码中有几处类型问题：

```python
# workflow.py - Optional[List[dict]] 但实际存的是 Pydantic 模型
requirements: Optional[List[dict]]

# llm_client.py - 返回类型不精确
def chat(...) -> Union[str, ChatResponse]:  # 调用方不知道什么时候返回哪个

# case_reviewer.py - 类型注解与实现不一致
def review_all(self, requirements: List[Union[Dict, Requirement]], ...) -> Dict[str, Any]:
# 实际返回的是 ReviewAllResult.to_dict()，但注解写的是 Dict[str, Any]
```

### 优化方案

添加 `mypy.ini` 或在 `pyproject.toml` 中配置：

```ini
# mypy.ini
[mypy]
python_version = 3.11
strict = false
ignore_missing_imports = true
check_untyped_defs = true

[mypy-core.*]
disallow_untyped_defs = true
```

同时修复现有的类型不一致问题。

### 涉及文件

- `mypy.ini` — 新建
- `core/agents/workflow.py`
- `core/utils/llm_client.py`

---

## 优先级汇总（最终完整版）

| Issue | 标题 | 类型 | 难度 | 优先级 |
|-------|------|------|------|--------|
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | 低 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | 低 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | 低 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | 中 | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | 低 | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | 低 | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | 低 | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | 低 | P0 |
| #24 | requirements.txt 缺少依赖且有未使用依赖 | Bug | 低 | P0 |
| #27 | conftest.py OUTPUT_DIR 变量遮蔽 | Bug | 低 | P0 |
| #28 | package.json 放错目录导致 npx 找不到配置 | Bug | 中 | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | 中 | P1 |
| #4 | Tool Calling | 功能 | 高 | P1 |
| #5 | Human-in-the-loop | 功能 | 中 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | 中 | P1 |
| #14 | ID 格式正则限制过严 | Bug | 低 | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | 低 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | 中 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | 中 | P1 |
| #20 | 缺少单元测试 | 测试 | 中 | P1 |
| #21 | 缺少日志系统 | 可观测性 | 低 | P1 |
| #25 | main.py 与 main_v2.py 并存职责不清 | 重构 | 低 | P1 |
| #26 | generate_allure_from_results.py 硬编码 | Bug | 低 | P1 |
| #32 | pytest.ini 放错目录且 testpaths 不匹配 | Bug | 低 | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | 低 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | 低 | P2 |
| #23 | 需求文档示例太简单 | 文档 | 低 | P2 |
| #29 | README.md 环境变量说明错误 | 文档 | 低 | P2 |
| #30 | midscene.config.ts 放错目录且配置重复 | 重构 | 低 | P2 |
| #31 | temp/ 目录和调试文件被提交到仓库 | 清理 | 低 | P2 |
| #33 | optimize_test_cases_node 是死代码 | 清理 | 低 | P2 |
| #34 | 缺少 CI/CD 配置 | 工程化 | 中 | P2 |
| #35 | 缺少类型检查配置 | 代码质量 | 低 | P2 |

---

## Issue 36：.mcp.json 包含真实 GitHub Token，已泄露到 Git 仓库

**标签**: `security` `critical` `priority-critical`

### 问题描述

`.mcp.json` 文件包含了一个真实的 GitHub Personal Access Token，并且已经被提交到 Git 仓库：

```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
      }
    }
  }
}
```

这是一个**严重的安全问题**：
- Token 已经暴露在公开仓库中（如果推送到 GitHub）
- 任何人都可以用这个 Token 访问你的 GitHub 账户
- Token 在 Git 历史中永久存在，即使删除文件也能找回

### 紧急处理步骤

**1. 立即撤销 Token：**
- 访问 GitHub Settings → Developer settings → Personal access tokens
- 找到这个 Token 并立即 Revoke（撤销）

**2. 从 Git 历史中彻底删除：**
```bash
# 使用 git-filter-repo 或 BFG Repo-Cleaner 清理历史
git filter-repo --path .mcp.json --invert-paths
# 或
bfg --delete-files .mcp.json
```

**3. 更新 .gitignore：**
```gitignore
# MCP 配置（包含敏感信息）
.mcp.json
```

**4. 创建模板文件：**
```json
// .mcp.json.example
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

**5. 从环境变量读取：**
```json
// .mcp.json（新版本，不提交到 Git）
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 涉及文件

- `.mcp.json` — 立即删除并加入 .gitignore
- `.mcp.json.example` — 新建模板文件
- `.gitignore` — 添加 `.mcp.json`

---

## Issue 37：QUICKSTART.md 中的环境变量名称错误（ANTHROPIC_API_KEY）

**标签**: `documentation` `priority-high`

### 问题描述

`docs/QUICKSTART.md` 中的配置说明使用了错误的环境变量名：

```markdown
在 `.env` 文件中填入你的Claude API密钥：
ANTHROPIC_API_KEY=sk-ant-xxxxx  ← 错误！
```

但项目实际使用的是 `LLM_KEY`（在 `.env.example` 和 `config.py` 中定义）。

同时文档说"提示 'ANTHROPIC_API_KEY not found'"，但代码中从未检查这个变量名。

### 优化方案

统一更新为 `LLM_KEY`：
```markdown
在 `.env` 文件中填入你的 LLM API 密钥：
LLM_KEY=your_api_key_here
LLM_MODEL=gpt-3.5-turbo  # 或其他模型
```

### 涉及文件

- `docs/QUICKSTART.md`

---

## Issue 38：tests/ 目录有大量测试文件但从未在 CI 中运行

**标签**: `testing` `priority-medium`

### 问题描述

`tests/unit/` 和 `tests/integration/` 目录下有 15+ 个测试文件：

```
tests/unit/
├── test_analyzer_core.py
├── test_improved_analyzer.py
├── test_llm_client.py
├── test_llm_debug.py
├── test_llm.py
├── test_manual.py
├── test_pydantic_models.py
├── test_requirement_analyzer_improved.py
├── test_requirement_model_only.py
└── test_simple_pydantic.py

tests/integration/
├── test_allure_reporter.py
├── test_executor.py
├── test_main_flow.py
├── test_midscene_generator.py
└── test_workflow.py
```

但：
- 没有 CI 配置，这些测试从未自动运行
- 不知道哪些测试是通过的，哪些是失败的
- 测试文件命名混乱（`test_llm.py` vs `test_llm_debug.py` vs `test_llm_client.py`）
- 有些测试可能是临时调试文件（`test_manual.py`、`test_llm_debug.py`）

### 优化方案

**1. 清理测试文件：**
- 删除调试文件（`test_manual.py`、`test_llm_debug.py`）
- 合并重复测试（`test_llm.py` + `test_llm_client.py`）
- 重命名不清晰的文件（`test_improved_analyzer.py` → `test_requirement_analyzer_v2.py`）

**2. 运行所有测试验证状态：**
```bash
pytest tests/ -v --tb=short
```

**3. 修复失败的测试**

**4. 添加 CI 配置（见 Issue #34）**

### 涉及文件

- `tests/unit/` — 清理和重命名
- `tests/integration/` — 验证测试状态

---

## Issue 39：ProjectSettings.llm_api_key 默认值为空字符串，导致启动时不报错

**标签**: `bug` `priority-medium`

### 问题描述

`config.py` 中 `llm_api_key` 的默认值是空字符串：

```python
llm_api_key: str = Field(
    default="",  # ← 默认空字符串
    validation_alias=AliasChoices('llm_api_key', 'LLM_KEY'),
)
```

这导致：
- 用户忘记配置 `.env` 时，程序不会在启动时报错
- 直到第一次调用 LLM 时才会失败（浪费时间）
- `LLMConfig.validate_api_key()` 会检查空字符串，但 `ProjectSettings` 不会触发这个验证

### 优化方案

**方案 A**：移除默认值，强制用户配置：
```python
llm_api_key: str = Field(
    ...,  # 必填，无默认值
    validation_alias=AliasChoices('llm_api_key', 'LLM_KEY'),
)
```

**方案 B**：在 `get_settings()` 中检查：
```python
def get_settings() -> ProjectSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ProjectSettings()
        # 启动时检查关键配置
        if not _settings_instance.llm_api_key:
            raise ValueError("LLM_KEY 未配置，请在 .env 文件中设置")
    return _settings_instance
```

### 涉及文件

- `core/models/config.py`

---

## Issue 40：LLMConfig 定义了 retry_attempts 和 retry_delay，但 LLMClient 从未使用

**标签**: `tech-debt` `priority-low`

### 问题描述

`LLMConfig` 模型中定义了重试相关字段：

```python
class LLMConfig(BaseModel):
    retry_attempts: int = Field(default=3, ...)
    retry_delay: float = Field(default=1.0, ...)
```

但 `LLMClient` 的 `__init__()` 中从未读取这两个字段：

```python
def __init__(self, api_key, model, base_url, temperature, max_tokens):
    # retry_attempts 和 retry_delay 从未被使用
    self.temperature = temperature
    self.max_tokens = max_tokens
    # 没有 self.retry_attempts = ...
```

而且 `LLMClient.chat()` 也没有实现重试逻辑（Issue #7 已提出）。

### 优化方案

在实现 Issue #7（重试机制）时，使用这两个配置字段。

### 涉及文件

- `core/models/config.py`
- `core/utils/llm_client.py`

---

## 最终优先级汇总

| Issue | 标题 | 类型 | 难度 | 优先级 |
|-------|------|------|------|--------|
| **#36** | **.mcp.json 包含真实 GitHub Token** | **安全** | **低** | **🔴 CRITICAL** |
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | 低 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | 低 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | 低 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | 中 | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | 低 | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | 低 | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | 低 | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | 低 | P0 |
| #24 | requirements.txt 缺少依赖且有未使用依赖 | Bug | 低 | P0 |
| #27 | conftest.py OUTPUT_DIR 变量遮蔽 | Bug | 低 | P0 |
| #28 | package.json 放错目录导致 npx 找不到配置 | Bug | 中 | P0 |
| #37 | QUICKSTART.md 环境变量名称错误 | 文档 | 低 | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | 中 | P1 |
| #4 | Tool Calling | 功能 | 高 | P1 |
| #5 | Human-in-the-loop | 功能 | 中 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | 中 | P1 |
| #14 | ID 格式正则限制过严 | Bug | 低 | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | 低 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | 中 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | 中 | P1 |
| #20 | 缺少单元测试 | 测试 | 中 | P1 |
| #21 | 缺少日志系统 | 可观测性 | 低 | P1 |
| #25 | main.py 与 main_v2.py 并存职责不清 | 重构 | 低 | P1 |
| #26 | generate_allure_from_results.py 硬编码 | Bug | 低 | P1 |
| #32 | pytest.ini 放错目录且 testpaths 不匹配 | Bug | 低 | P1 |
| #38 | tests/ 有大量测试但从未在 CI 运行 | 测试 | 中 | P1 |
| #39 | llm_api_key 默认空字符串不报错 | Bug | 低 | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | 低 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | 低 | P2 |
| #23 | 需求文档示例太简单 | 文档 | 低 | P2 |
| #29 | README.md 环境变量说明错误 | 文档 | 低 | P2 |
| #30 | midscene.config.ts 放错目录且配置重复 | 重构 | 低 | P2 |
| #31 | temp/ 目录和调试文件被提交到仓库 | 清理 | 低 | P2 |
| #33 | optimize_test_cases_node 是死代码 | 清理 | 低 | P2 |
| #34 | 缺少 CI/CD 配置 | 工程化 | 中 | P2 |
| #35 | 缺少类型检查配置 | 代码质量 | 低 | P2 |
| #40 | LLMConfig 定义了重试字段但未使用 | 技术债 | 低 | P2 |

---

## 总结

共发现 **40 个优化点**，分为：

- **🔴 CRITICAL（1个）**：安全问题，必须立即处理
- **P0（13个）**：严重 Bug 和缺失依赖，影响基本功能
- **P1（14个）**：重要功能增强和工程质量提升
- **P2（12个）**：易用性改进和代码清理

建议处理顺序：
1. **立即处理 #36**（撤销 GitHub Token）
2. **第一批（P0）**：修复 Bug，补全依赖，消除技术债
3. **第二批（P1）**：核心功能增强（Tool Calling、并行、可观测性）
4. **第三批（P2）**：易用性和文档完善

---

## Issue 41：test_workflow.py 的 import 路径是旧路径，运行时直接报错

**标签**: `bug` `priority-high`

### 问题描述

`tests/integration/test_workflow.py` 使用了重构前的旧导入路径：

```python
# 错误的旧路径（缺少 core. 前缀）
from agents.workflow import (       # ❌ 应该是 core.agents.workflow
    AgentState,
    analyze_requirements_node,
    ...
)
```

同时 Mock 的路径也是错的：
```python
@patch("agents.workflow.RequirementAnalyzer")   # ❌
@patch("agents.workflow.TestCaseGenerator")     # ❌
# 应该是
@patch("core.agents.workflow.RequirementAnalyzer")
@patch("core.agents.workflow.TestCaseGenerator")
```

这意味着这个集成测试文件**从来没有成功运行过**。

### 涉及文件

- `tests/integration/test_workflow.py`

---

## Issue 42：test_analyzer_core.py 不是标准 pytest 测试，无法被 pytest 自动发现

**标签**: `bug` `testing` `priority-medium`

### 问题描述

`tests/unit/test_analyzer_core.py` 的测试函数不符合 pytest 规范：

```python
# 当前：自定义测试框架，pytest 无法识别
def test_core_functionality():
    # 用 print 输出，用 return True/False 表示结果
    print("✅ 返回类型: ...")
    return True  # ← pytest 不看返回值

def test_error_handling():
    return True

# 入口是 if __name__ == "__main__"，不是 pytest 的方式
if __name__ == "__main__":
    for test_name, test_func in tests:
        if test_func():  # ← pytest 不这样调用
            passed += 1
```

pytest 运行时会发现这些函数，但因为没有 `assert` 语句，所有测试都会"通过"（即使逻辑是错的）。

### 优化方案

改写为标准 pytest 格式：

```python
import pytest
from core.models.requirement import Requirement, RequirementAnalysisResult

class TestRequirementAnalyzerCore:

    def test_analyze_structured_returns_pydantic_model(self):
        analyzer = RequirementAnalyzerCore()
        result = analyzer.analyze_structured(VALID_REQUIREMENT)
        assert isinstance(result, RequirementAnalysisResult)
        assert result.total_count == 1

    def test_analyze_raises_on_empty_input(self):
        analyzer = RequirementAnalyzerCore()
        with pytest.raises(ValueError, match="至少需要10个字符"):
            analyzer.analyze_structured("")

    def test_extract_json_from_markdown_block(self):
        analyzer = RequirementAnalyzerCore()
        content = '```json\n{"key": "value"}\n```'
        result = analyzer._extract_json(content)
        assert result == {"key": "value"}
```

### 涉及文件

- `tests/unit/test_analyzer_core.py`
- `tests/unit/` 下其他类似文件

---

## Issue 43：PHASE3_DESIGN.md 中的设计与实际实现已严重偏离

**标签**: `documentation` `priority-low`

### 问题描述

`docs/PHASE3_DESIGN.md` 是阶段3的设计文档，但实际实现与设计有多处不符：

**1. 设计中的模块结构：**
```
automation/
├── script_generator.py      # 设计中保留
├── midscene_generator.py    # 设计中新增
├── element_locator.py       # 设计中新增，实际未实现
└── test_executor.py         # 设计中新增
```
实际上 `element_locator.py` 从未被创建，`script_generator.py` 也不存在（被 `midscene_generator.py` 替代）。

**2. 设计中的 AgentState 扩展：**
```python
# 设计文档中
class AgentState(TypedDict):
    generated_scripts: List[str]   # 设计是列表
    execution_results: List[Dict]  # 设计是列表
```
实际实现：
```python
generated_script: Optional[str]   # 实际是单个字符串
execution_results: Optional[dict] # 实际是单个字典
```

**3. 设计中的 Midscene API：**
```typescript
// 设计文档中
const midscene = new Midscene(page);
await midscene.ai('...');
```
实际生成的脚本使用：
```typescript
// 实际实现
const test = base.extend<{ai: any}>(PlaywrightAiFixture());
await ai('...');
```

### 优化方案

更新设计文档使其与实际实现一致，或者在文档顶部标注"此文档为历史设计，实际实现见代码"。

### 涉及文件

- `docs/PHASE3_DESIGN.md`

---

## Issue 44：LLMConfig.validate_model() 在初始化时打印警告，污染测试输出

**标签**: `code-quality` `priority-low`

### 问题描述

`LLMConfig.validate_model()` 在验证时直接 `print()` 警告：

```python
@field_validator('model')
@classmethod
def validate_model(cls, v):
    valid_models = ["gpt-4", "qwen-plus", ...]
    if v not in valid_models:
        print(f"警告: 使用了未知的模型名称 '{v}'，请确保该模型可用")  # ← 污染输出
    return v
```

这导致：
- 每次创建 `LLMConfig` 实例都会打印到 stdout
- 运行测试时输出被污染
- 使用自定义模型名（如 `qwen-max-latest`）时每次都有警告

### 优化方案

改用 Python 标准 `warnings` 模块或 logging：

```python
import warnings

@field_validator('model')
@classmethod
def validate_model(cls, v):
    known_models = [...]
    if v not in known_models:
        warnings.warn(
            f"未知模型名称 '{v}'，请确保该模型可用",
            UserWarning,
            stacklevel=2
        )
    return v
```

### 涉及文件

- `core/models/config.py`

---

## Issue 45：缺少 pyproject.toml，项目元数据分散在多个文件

**标签**: `enhancement` `code-quality` `priority-low`

### 问题描述

现代 Python 项目应该使用 `pyproject.toml` 统一管理项目元数据，但当前项目：
- 没有 `pyproject.toml`
- 项目名称、版本在 `config/config.yaml` 里
- pytest 配置在 `config/pytest.ini` 里（放错目录）
- 没有 `setup.py` 或 `setup.cfg`
- 无法用 `pip install -e .` 安装为可编辑包

这导致 `sys.path.append(...)` 这样的 hack 出现在测试文件中：
```python
# tests/unit/test_analyzer_core.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ← 不应该这样做
```

### 优化方案

创建 `pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "ai-test-platform"
version = "0.1.0"
description = "AI 驱动的端到端测试自动化平台"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/integration"]
asyncio_mode = "auto"
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py311"
```

然后在项目根目录运行 `pip install -e .`，所有 `sys.path` hack 都可以删除。

### 涉及文件

- `pyproject.toml` — 新建
- `config/pytest.ini` — 内容迁移到 pyproject.toml 后删除
- `tests/unit/test_analyzer_core.py` — 删除 sys.path hack

---

## 最终完整汇总（共 45 个 Issue）

| Issue | 标题 | 类型 | 优先级 |
|-------|------|------|--------|
| **#36** | **.mcp.json 包含真实 GitHub Token** | 安全 | **🔴 CRITICAL** |
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | P0 |
| #24 | requirements.txt 缺少依赖且有未使用依赖 | Bug | P0 |
| #27 | conftest.py OUTPUT_DIR 变量遮蔽 | Bug | P0 |
| #28 | package.json 放错目录导致 npx 找不到配置 | Bug | P0 |
| #37 | QUICKSTART.md 环境变量名称错误 | 文档 | P0 |
| #41 | test_workflow.py import 路径是旧路径 | Bug | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | P1 |
| #4 | Tool Calling | 功能 | P1 |
| #5 | Human-in-the-loop | 功能 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | P1 |
| #14 | ID 格式正则限制过严 | Bug | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | P1 |
| #20 | 缺少单元测试 | 测试 | P1 |
| #21 | 缺少日志系统 | 可观测性 | P1 |
| #25 | main.py 与 main_v2.py 并存职责不清 | 重构 | P1 |
| #26 | generate_allure_from_results.py 硬编码 | Bug | P1 |
| #32 | pytest.ini 放错目录且 testpaths 不匹配 | Bug | P1 |
| #38 | tests/ 有大量测试但从未在 CI 运行 | 测试 | P1 |
| #39 | llm_api_key 默认空字符串不报错 | Bug | P1 |
| #42 | test_analyzer_core.py 不是标准 pytest 格式 | Bug | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | P2 |
| #23 | 需求文档示例太简单 | 文档 | P2 |
| #29 | README.md 环境变量说明错误 | 文档 | P2 |
| #30 | midscene.config.ts 放错目录且配置重复 | 重构 | P2 |
| #31 | temp/ 目录和调试文件被提交到仓库 | 清理 | P2 |
| #33 | optimize_test_cases_node 是死代码 | 清理 | P2 |
| #34 | 缺少 CI/CD 配置 | 工程化 | P2 |
| #35 | 缺少类型检查配置 | 代码质量 | P2 |
| #40 | LLMConfig 定义了重试字段但未使用 | 技术债 | P2 |
| #43 | PHASE3_DESIGN.md 与实际实现严重偏离 | 文档 | P2 |
| #44 | LLMConfig.validate_model() 污染测试输出 | 代码质量 | P2 |
| #45 | 缺少 pyproject.toml，项目元数据分散 | 工程化 | P2 |

