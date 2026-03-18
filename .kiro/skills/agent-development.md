---
name: agent-development
description: Agent开发相关的技能和最佳实践
tags: [agent, llm, langgraph]
---

# Agent开发技能

## LangGraph状态机设计

### 基础状态图结构
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[list, operator.add]
    requirement_doc: str
    parsed_requirements: dict
    test_cases: list
    execution_results: dict
    current_step: str

def create_workflow():
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("parse_document", parse_document_node)
    workflow.add_node("analyze_requirements", analyze_requirements_node)
    workflow.add_node("generate_test_cases", generate_test_cases_node)
    workflow.add_node("review_test_cases", review_test_cases_node)
    workflow.add_node("execute_tests", execute_tests_node)
    
    # 定义边
    workflow.set_entry_point("parse_document")
    workflow.add_edge("parse_document", "analyze_requirements")
    workflow.add_edge("analyze_requirements", "generate_test_cases")
    
    # 条件边（需要人工审核）
    workflow.add_conditional_edges(
        "generate_test_cases",
        should_review,
        {
            "review": "review_test_cases",
            "execute": "execute_tests"
        }
    )
    
    workflow.add_edge("review_test_cases", "execute_tests")
    workflow.add_edge("execute_tests", END)
    
    return workflow.compile()
```

### 节点实现模式
```python
async def analyze_requirements_node(state: AgentState) -> AgentState:
    """需求分析节点"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import SystemMessage, HumanMessage
    
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    
    # 构建prompt
    system_prompt = SystemMessage(content=REQUIREMENT_ANALYSIS_PROMPT)
    user_message = HumanMessage(content=state["requirement_doc"])
    
    # 调用LLM
    response = await llm.ainvoke([system_prompt, user_message])
    
    # 解析响应
    import json
    parsed_requirements = json.loads(response.content)
    
    # 更新状态
    return {
        **state,
        "parsed_requirements": parsed_requirements,
        "current_step": "analyze_requirements",
        "messages": [f"分析完成，识别到{len(parsed_requirements['requirements'])}个需求"]
    }
```

## Tool Calling实现

### 定义工具
```python
from langchain_core.tools import tool

@tool
def extract_pdf_content(file_path: str) -> str:
    """从PDF文件提取文本内容
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        提取的文本内容
    """
    import PyMuPDF
    doc = PyMuPDF.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@tool
def validate_test_case(test_case: dict) -> dict:
    """验证测试用例格式和完整性
    
    Args:
        test_case: 测试用例字典
        
    Returns:
        验证结果和建议
    """
    issues = []
    
    required_fields = ["id", "title", "steps", "expected"]
    for field in required_fields:
        if field not in test_case:
            issues.append(f"缺少必填字段: {field}")
    
    if "steps" in test_case and len(test_case["steps"]) == 0:
        issues.append("测试步骤不能为空")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "suggestions": ["添加更多边界值测试"] if len(issues) == 0 else []
    }

# 绑定工具到LLM
tools = [extract_pdf_content, validate_test_case]
llm_with_tools = llm.bind_tools(tools)
```

### 工具调用循环
```python
async def agent_with_tools(state: AgentState):
    """带工具调用的Agent"""
    messages = state["messages"]
    
    while True:
        response = await llm_with_tools.ainvoke(messages)
        
        # 检查是否有工具调用
        if not response.tool_calls:
            break
        
        # 执行工具
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # 查找并执行工具
            tool_func = next(t for t in tools if t.name == tool_name)
            result = await tool_func.ainvoke(tool_args)
            
            # 添加工具结果到消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            })
        
        messages.append(response)
    
    return {"messages": messages}
```

## Prompt工程技巧

### 结构化输出
```python
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class TestCase(BaseModel):
    id: str = Field(description="测试用例ID，格式TC_XXX")
    title: str = Field(description="测试用例标题")
    priority: str = Field(description="优先级: critical/high/medium/low")
    steps: list[dict] = Field(description="测试步骤列表")
    expected: str = Field(description="预期结果")

parser = JsonOutputParser(pydantic_object=TestCase)

prompt = f"""
生成测试用例，输出格式：
{parser.get_format_instructions()}

需求：{{requirement}}
"""
```

### Few-Shot Learning
```python
FEW_SHOT_EXAMPLES = """
示例1：
需求：用户应该能够使用邮箱和密码登录
测试用例：
{{
  "id": "TC_LOGIN_001",
  "title": "正常登录流程",
  "priority": "critical",
  "steps": [
    {{"action": "打开登录页面", "data": "https://app.com/login"}},
    {{"action": "在邮箱输入框输入", "data": "test@example.com"}},
    {{"action": "在密码输入框输入", "data": "Password123!"}},
    {{"action": "点击登录按钮"}}
  ],
  "expected": "跳转到首页，右上角显示用户邮箱"
}}

示例2：
需求：购物车商品数量不能超过99
测试用例：
{{
  "id": "TC_CART_001",
  "title": "购物车数量边界值测试",
  "priority": "high",
  "steps": [
    {{"action": "添加商品到购物车", "data": {{"quantity": 99}}}},
    {{"action": "尝试增加数量"}}
  ],
  "expected": "显示错误提示：数量不能超过99"
}}

现在基于以下需求生成测试用例：
{requirement}
"""
```

### Chain of Thought
```python
COT_PROMPT = """
请按以下步骤分析需求并生成测试用例：

步骤1：理解需求
- 核心功能是什么？
- 涉及哪些用户角色？
- 有哪些业务规则？

步骤2：识别测试场景
- 正常流程
- 边界条件
- 异常情况
- 兼容性要求

步骤3：设计测试用例
- 为每个场景设计具体步骤
- 定义测试数据
- 明确预期结果

步骤4：优先级排序
- 根据业务影响和风险评估优先级

需求内容：
{requirement}

请按上述步骤思考并输出最终的测试用例JSON。
"""
```

## 错误处理和重试

### 指数退避重试
```python
import asyncio
from functools import wraps

def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= exponential_base
                    else:
                        raise last_exception
            
        return wrapper
    return decorator

@retry_with_exponential_backoff(max_retries=3)
async def call_llm_with_retry(prompt: str):
    return await llm.ainvoke(prompt)
```

### 响应验证
```python
def validate_llm_response(response: str, expected_schema: dict) -> bool:
    """验证LLM响应是否符合预期格式"""
    try:
        import json
        from jsonschema import validate
        
        data = json.loads(response)
        validate(instance=data, schema=expected_schema)
        return True
    except Exception as e:
        print(f"验证失败: {e}")
        return False

# 使用
response = await llm.ainvoke(prompt)
if not validate_llm_response(response.content, TEST_CASE_SCHEMA):
    # 重新生成或使用默认值
    response = await llm.ainvoke(prompt + "\n请严格按照JSON schema输出")
```

## 成本优化

### 响应缓存
```python
from functools import lru_cache
import hashlib

class LLMCache:
    def __init__(self):
        self.cache = {}
    
    def get_cache_key(self, prompt: str, model: str) -> str:
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_or_generate(self, prompt: str, model: str, llm):
        cache_key = self.get_cache_key(prompt, model)
        
        if cache_key in self.cache:
            print(f"缓存命中: {cache_key[:8]}...")
            return self.cache[cache_key]
        
        response = await llm.ainvoke(prompt)
        self.cache[cache_key] = response
        return response

cache = LLMCache()
```

### Token计数和限制
```python
import tiktoken

def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """计算文本的token数量"""
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))

def truncate_to_token_limit(text: str, max_tokens: int = 4000) -> str:
    """截断文本到指定token数量"""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)

# 使用
if count_tokens(document) > 8000:
    # 分块处理
    chunks = split_document(document, chunk_size=4000)
    results = [await process_chunk(chunk) for chunk in chunks]
```

## 可观测性

### 日志记录
```python
import logging
from datetime import datetime

class AgentLogger:
    def __init__(self, agent_name: str):
        self.logger = logging.getLogger(agent_name)
        self.agent_name = agent_name
    
    def log_decision(self, step: str, reasoning: str, action: str):
        """记录Agent决策过程"""
        self.logger.info(f"""
        Agent: {self.agent_name}
        Step: {step}
        Reasoning: {reasoning}
        Action: {action}
        Timestamp: {datetime.now().isoformat()}
        """)
    
    def log_llm_call(self, prompt: str, response: str, tokens: int, cost: float):
        """记录LLM调用"""
        self.logger.debug(f"""
        LLM Call:
        Prompt Length: {len(prompt)} chars
        Response Length: {len(response)} chars
        Tokens: {tokens}
        Cost: ${cost:.4f}
        """)

logger = AgentLogger("RequirementAnalyzer")
```

### 追踪链路
```python
from contextvars import ContextVar
import uuid

trace_id: ContextVar[str] = ContextVar('trace_id')

def start_trace():
    """开始新的追踪链路"""
    trace_id.set(str(uuid.uuid4()))
    return trace_id.get()

def get_trace_id():
    """获取当前追踪ID"""
    return trace_id.get()

# 在每个节点中使用
async def node_with_tracing(state: AgentState):
    tid = get_trace_id()
    logger.info(f"[{tid}] 执行节点: analyze_requirements")
    # ... 节点逻辑
```
