# LangGraph 学习指南

## 核心概念速查

### 1. State（状态）

```python
from typing import TypedDict

class AgentState(TypedDict):
    requirement_text: str      # 输入
    requirements: list         # 中间结果
    test_cases: list           # 输出
    review_passed: bool        # 控制流
```

**作用**：所有 Agent 共享的数据结构

---

### 2. Node（节点）

```python
def my_node(state: AgentState) -> dict:
    # 读取状态
    input_data = state["requirement_text"]

    # 处理
    result = process(input_data)

    # 返回更新
    return {"requirements": result}
```

**要点**：
- 输入：整个 state
- 输出：要更新的字段（部分更新）

---

### 3. Edge（边）

```python
# 普通边：固定顺序
workflow.add_edge("A", "B")

# 条件边：动态路由
workflow.add_conditional_edges(
    "review",
    should_retry,  # 路由函数
    {"end": END, "retry": "generate"}
)
```

---

### 4. Graph（图）

```python
from langgraph.graph import StateGraph, END

# 1. 创建
workflow = StateGraph(AgentState)

# 2. 添加节点
workflow.add_node("analyze", analyze_node)
workflow.add_node("generate", generate_node)

# 3. 设置入口
workflow.set_entry_point("analyze")

# 4. 添加边
workflow.add_edge("analyze", "generate")
workflow.add_edge("generate", END)

# 5. 编译
app = workflow.compile()

# 6. 执行
result = app.invoke(initial_state)
```

---

## 项目代码对照

| 概念 | 项目文件 | 位置 |
|------|----------|------|
| State | `agents/workflow.py` | `AgentState` 类 |
| Node | `agents/workflow.py` | `analyze_requirements_node` 等函数 |
| Edge | `agents/workflow.py` | `build_workflow()` 中的 `add_edge` |
| Graph | `agents/workflow.py` | `build_workflow()` 函数 |
| 执行 | `main_v2.py` | `run_workflow()` |

---

## 学习路径

```
第1步：运行教程
    python docs/langgraph_tutorial.py

第2步：阅读源码
    agents/workflow.py

第3步：运行主程序
    python main_v2.py

第4步：运行测试
    pytest tests/test_workflow.py -v

第5步：完成练习
    修改节点函数，观察变化
```

---

## 练习题

### 练习1：添加新节点

在 `workflow.py` 中添加优化节点：

```python
def optimize_test_cases_node(state: AgentState) -> dict:
    """优化测试用例"""
    test_cases = state["test_cases"]

    # 优化逻辑
    optimized = []
    for tc in test_cases:
        # 添加缺失的字段
        if "priority" not in tc:
            tc["priority"] = "medium"
        optimized.append(tc)

    return {"test_cases": optimized}
```

### 练习2：修改评审逻辑

```python
def review_test_cases_node(state: AgentState) -> dict:
    test_cases = state["test_cases"]
    comments = []

    for tc in test_cases:
        if not tc.get("steps"):
            comments.append({"type": "missing_steps", "case_id": tc["id"]})
        if not tc.get("expected"):
            comments.append({"type": "missing_expected", "case_id": tc["id"]})

    return {
        "review_passed": len(comments) == 0,
        "review_comments": comments
    }
```

### 练习3：添加状态字段

```python
class AgentState(TypedDict):
    # ... 原有字段
    risk_level: Optional[str]  # 新增

def assess_risk_node(state: AgentState) -> dict:
    """风险评估节点"""
    requirements = state["requirements"]

    # 简单规则
    if len(requirements) > 5:
        return {"risk_level": "high"}
    return {"risk_level": "low"}
```

---

## 调试技巧

### 1. 打印状态变化

```python
def my_node(state: AgentState) -> dict:
    print(f"输入状态: {state}")
    result = process(state)
    print(f"输出更新: {result}")
    return result
```

### 2. 使用 stream 模式

```python
# 流式执行，可以看到每一步
for event in app.stream(initial_state):
    print(f"节点: {event}")
```

### 3. 可视化工作流

```python
from IPython.display import Image, display

# 生成流程图
display(Image(app.get_graph().draw_mermaid_png()))
```

---

## 常见问题

**Q: 节点函数返回什么？**
A: 返回要更新的字段字典，不是整个 state。

**Q: 如何实现循环？**
A: 使用条件边，返回到之前的节点。

**Q: 如何并行执行？**
A: 多个边指向同一个节点会并行执行。

**Q: 状态如何合并？**
A: LangGraph 自动合并返回的字段到状态中。

---

## 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [项目 workflow.py](../agents/workflow.py)
