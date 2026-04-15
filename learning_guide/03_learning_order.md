# 学习顺序 - 从简单到复杂

## 第1步: 工具模块 (utils/)
**为什么先学这个?** 这些是基础工具，其他模块都会用到

### 学习文件顺序:
1. `utils/project_paths.py` - 路径常量定义
2. `utils/llm_client.py` - LLM客户端封装

### 学习方法:
```python
# 1. 阅读代码，理解每个函数的作用
# 2. 运行简单测试
python -c "from utils.project_paths import OUTPUT_DIR; print(OUTPUT_DIR)"

# 3. 测试LLM客户端 (需要API密钥)
python test_llm.py
```

## 第2步: 文档解析 (parsers/)
**为什么第二学?** 这是数据输入的起点，逻辑简单

### 学习文件:
1. `parsers/markdown_parser.py` - Markdown文档解析

### 实践练习:
```python
# 测试解析功能
from parsers.markdown_parser import parse_markdown
content = parse_markdown("examples/requirement_login.md")
print(content)
```

## 第3步: 单个Agent (agents/)
**为什么第三学?** 理解AI Agent的基本工作原理

### 学习顺序:
1. `agents/requirement_analyzer.py` - 需求分析Agent
2. `agents/test_case_generator.py` - 测试用例生成Agent  
3. `agents/case_reviewer.py` - 测试用例评审Agent

### 学习方法:
```python
# 单独测试每个Agent
python -c "
from agents.requirement_analyzer import RequirementAnalyzer
analyzer = RequirementAnalyzer()
# 测试分析功能
"
```

## 第4步: 自动化执行 (automation/)
**为什么第四学?** 涉及外部工具，相对复杂

### 学习顺序:
1. `automation/midscene_generator.py` - 脚本生成器
2. `automation/test_executor.py` - 测试执行器
3. `automation/allure_reporter.py` - 报告生成器

## 第5步: 工作流编排 (agents/workflow.py)
**为什么最后学?** 这是最复杂的部分，整合了所有组件

### 学习重点:
1. LangGraph状态机概念
2. Agent间协作机制
3. 条件路由和反馈循环