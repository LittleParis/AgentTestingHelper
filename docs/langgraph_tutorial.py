"""
LangGraph 学习指南 - 基于本项目

这个文件通过项目实际代码讲解 LangGraph 的核心概念。
运行方式: python docs/langgraph_tutorial.py
"""

# ============================================================
# 第一部分：State（状态）- Agent 之间共享的数据
# ============================================================

print("=" * 60)
print("第一部分：State（状态）")
print("=" * 60)

"""
State 是一个 TypedDict，定义了所有 Agent 可以读写的共享数据。

类比：就像一个共享的白板，所有 Agent 都可以在上面读写。
"""

from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    """Agent 共享状态"""
    # 输入
    requirement_text: str                    # 原始需求文档

    # 中间结果
    requirements: Optional[List[dict]]       # 分析后的需求
    test_cases: Optional[List[dict]]         # 生成的测试用例

    # 控制流
    review_passed: Optional[bool]            # 评审是否通过
    iteration_count: int                     # 迭代次数

    # 输出
    agent_messages: List[dict]               # Agent 消息


# 创建一个状态实例
initial_state: AgentState = {
    "requirement_text": "用户登录功能...",
    "requirements": None,      # 初始为空
    "test_cases": None,        # 初始为空
    "review_passed": None,     # 初始为空
    "iteration_count": 0,      # 初始为 0
    "agent_messages": []       # 初始为空列表
}

print("初始状态:")
for key, value in initial_state.items():
    print(f"  {key}: {value}")


# ============================================================
# 第二部分：Node（节点）- 执行具体任务的函数
# ============================================================

print("\n" + "=" * 60)
print("第二部分：Node（节点）")
print("=" * 60)

"""
节点就是一个普通函数，接收状态，返回状态更新。

关键点：
1. 输入：当前状态（整个 state）
2. 输出：要更新的状态字段（部分更新，不是替换整个 state）
3. LangGraph 会自动合并返回的字段到状态中
"""

def analyze_requirements_node(state: AgentState) -> dict:
    """
    需求分析节点

    输入：state["requirement_text"]
    输出：{"requirements": [...], "requirement_summary": "..."}
    """
    print("\n[节点执行] analyze_requirements_node")

    # 从状态读取输入
    text = state["requirement_text"]

    # 模拟处理（实际会调用 LLM）
    result = {
        "requirements": [
            {"id": "REQ_001", "title": "用户登录"}
        ],
        "requirement_summary": "登录功能需求"
    }

    # 返回要更新的字段
    return {
        "requirements": result["requirements"],
        "requirement_summary": result["requirement_summary"],
        "current_step": "analyzed",
        "agent_messages": [{"role": "analyzer", "content": "分析完成"}]
    }


def generate_test_cases_node(state: AgentState) -> dict:
    """
    用例生成节点

    输入：state["requirements"]
    输出：{"test_cases": [...]}
    """
    print("\n[节点执行] generate_test_cases_node")

    # 从状态读取上一个节点的输出
    requirements = state["requirements"]

    # 模拟生成
    test_cases = [
        {"id": "TC_001", "title": "正确登录"},
        {"id": "TC_002", "title": "密码错误"}
    ]

    return {
        "test_cases": test_cases,
        "current_step": "generated"
    }


# 手动模拟节点执行（理解数据流）
print("\n手动模拟节点执行:")
state1 = initial_state
print(f"初始状态: requirements={state1['requirements']}")

update1 = analyze_requirements_node(state1)
state2 = {**state1, **update1}  # 合并更新
print(f"分析后: requirements={state2['requirements']}")

update2 = generate_test_cases_node(state2)
state3 = {**state2, **update2}  # 合并更新
print(f"生成后: test_cases={state3['test_cases']}")


# ============================================================
# 第三部分：Edge（边）- 节点之间的连接
# ============================================================

print("\n" + "=" * 60)
print("第三部分：Edge（边）")
print("=" * 60)

"""
边定义了节点之间的执行顺序。

类型：
1. 普通边（add_edge）：A → B，固定顺序
2. 条件边（add_conditional_edges）：根据状态选择下一个节点
"""

# 普通边示例
print("""
普通边（固定顺序）:

    analyze_requirements ──→ generate_test_cases ──→ review

代码:
    workflow.add_edge("analyze_requirements", "generate_test_cases")
    workflow.add_edge("generate_test_cases", "review")
""")

# 条件边示例
print("""
条件边（动态路由）:

                    ┌── passed ──→ END
    review ──→ 判断 ┤
                    └── failed ──→ regenerate

代码:
    def should_regenerate(state) -> str:
        if state["review_passed"]:
            return "end"
        return "regenerate"

    workflow.add_conditional_edges(
        "review",
        should_regenerate,
        {"end": END, "regenerate": "generate_test_cases"}
    )
""")


# ============================================================
# 第四部分：Graph（图）- 组装完整工作流
# ============================================================

print("\n" + "=" * 60)
print("第四部分：Graph（图）")
print("=" * 60)

from langgraph.graph import StateGraph, END

# 步骤1：创建状态图
workflow = StateGraph(AgentState)

# 步骤2：添加节点
workflow.add_node("analyze", analyze_requirements_node)
workflow.add_node("generate", generate_test_cases_node)

# 步骤3：设置入口点
workflow.set_entry_point("analyze")

# 步骤4：添加边
workflow.add_edge("analyze", "generate")
workflow.add_edge("generate", END)

# 步骤5：编译
app = workflow.compile()

print("""
工作流构建步骤:

1. StateGraph(AgentState)  - 创建状态图
2. add_node(name, func)    - 添加节点
3. set_entry_point(node)   - 设置入口
4. add_edge(A, B)          - 添加边
5. compile()               - 编译成可执行应用
""")


# ============================================================
# 第五部分：执行工作流
# ============================================================

print("\n" + "=" * 60)
print("第五部分：执行工作流")
print("=" * 60)

# 准备初始状态
test_state: AgentState = {
    "requirement_text": "用户登录功能",
    "requirements": None,
    "requirement_summary": None,
    "test_cases": None,
    "review_passed": None,
    "review_comments": None,
    "iteration_count": 0,
    "max_iterations": 2,
    "feedback": [],
    "current_step": "init",
    "agent_messages": []
}

# 执行
print("\n执行工作流...")
final_state = app.invoke(test_state)

print("\n最终状态:")
print(f"  requirements: {final_state['requirements']}")
print(f"  test_cases: {final_state['test_cases']}")
print(f"  messages: {final_state['agent_messages']}")


# ============================================================
# 第六部分：条件边与循环
# ============================================================

print("\n" + "=" * 60)
print("第六部分：条件边与循环")
print("=" * 60)

def review_node(state: AgentState) -> dict:
    """评审节点"""
    test_cases = state["test_cases"]
    passed = len(test_cases) >= 2  # 简单规则：至少2个用例
    return {
        "review_passed": passed,
        "current_step": "reviewed"
    }


def should_retry(state: AgentState) -> str:
    """路由函数：决定是否重试"""
    if state["review_passed"]:
        return "end"
    if state["iteration_count"] >= 2:
        return "end"
    return "retry"


def increment_iteration(state: AgentState) -> dict:
    """增加迭代计数"""
    return {"iteration_count": state["iteration_count"] + 1}


# 构建带循环的工作流
workflow2 = StateGraph(AgentState)

workflow2.add_node("analyze", analyze_requirements_node)
workflow2.add_node("generate", generate_test_cases_node)
workflow2.add_node("review", review_node)
workflow2.add_node("increment", increment_iteration)

workflow2.set_entry_point("analyze")

# 普通边
workflow2.add_edge("analyze", "generate")
workflow2.add_edge("generate", "review")

# 条件边：评审后决定下一步
workflow2.add_conditional_edges(
    "review",
    should_retry,
    {
        "end": END,
        "retry": "increment"
    }
)

# 迭代后重新生成
workflow2.add_edge("increment", "generate")

app2 = workflow2.compile()

print("""
带循环的工作流:

    START → analyze → generate → review
                               ↓
                         should_retry?
                         ↙        ↘
                    retry          end → END
                     ↓
                 increment
                     ↓
                  generate ←──┘
""")


# ============================================================
# 第七部分：实际项目代码对照
# ============================================================

print("\n" + "=" * 60)
print("第七部分：项目代码对照")
print("=" * 60)

print("""
项目文件结构:

agents/
├── workflow.py          # LangGraph 工作流定义
├── requirement_analyzer.py  # 需求分析 Agent
├── test_case_generator.py   # 用例生成 Agent
└── (待添加) case_reviewer.py # 用例评审 Agent

main_v2.py               # 使用工作流的主程序
tests/test_workflow.py   # 工作流测试

学习建议:
1. 先看 workflow.py 中的 AgentState 定义
2. 再看各个节点函数（analyze_requirements_node 等）
3. 最后看 build_workflow() 如何组装
4. 运行 main_v2.py 观察执行流程
5. 修改节点函数，观察变化
""")


# ============================================================
# 第八部分：练习题
# ============================================================

print("\n" + "=" * 60)
print("第八部分：练习题")
print("=" * 60)

print("""
练习1：添加新节点
-----------------
在 workflow.py 中添加一个新节点 "optimize"，用于优化测试用例。
提示：
1. 定义 optimize_test_cases_node 函数
2. 在 build_workflow 中添加节点
3. 修改边的连接

练习2：修改评审逻辑
------------------
修改 review_test_cases_node，添加更多评审规则：
- 检查每个用例是否有 steps
- 检查每个用例是否有 expected
- 检查用例标题长度

练习3：添加新的状态字段
----------------------
在 AgentState 中添加 "risk_level" 字段，
并创建一个风险评估节点来填充它。

练习4：实现并行执行
------------------
使用 LangGraph 的并行功能，让多个需求同时生成测试用例。
提示：研究 langgraph 的 fan-out/fan-in 模式。
""")


print("\n" + "=" * 60)
print("学习指南完成！")
print("=" * 60)
print("""
下一步：
1. 阅读 agents/workflow.py 源码
2. 运行 main_v2.py 观察实际执行
3. 完成上面的练习题
4. 查看 LangGraph 官方文档: https://langchain-ai.github.io/langgraph/
""")
