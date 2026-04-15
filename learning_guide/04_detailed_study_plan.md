# 详细学习计划

## Day 1: 基础工具模块

### 上午: 项目路径管理
```python
# 文件: utils/project_paths.py
# 学习目标: 理解项目目录结构

# 练习1: 打印所有路径
from utils.project_paths import *
print("输出目录:", OUTPUT_DIR)
print("生成脚本目录:", GENERATED_TESTS_DIR)
print("Allure结果目录:", ALLURE_RESULTS_DIR)

# 练习2: 创建目录
from utils.project_paths import ensure_runtime_directories
ensure_runtime_directories()
```

### 下午: LLM客户端
```python
# 文件: utils/llm_client.py
# 学习目标: 理解如何调用LLM

# 练习1: 理解Message类
from utils.llm_client import Message
msg = Message.user("你好")
print(msg.to_dict())

# 练习2: 测试LLM调用 (需要API密钥)
from utils.llm_client import get_llm_client
client = get_llm_client()
response = client.chat_simple("1+1等于几?")
print(response)
```

## Day 2: 文档解析和需求分析

### 上午: Markdown解析
```python
# 文件: parsers/markdown_parser.py
# 学习目标: 理解文档解析流程

# 练习1: 解析示例文档
from parsers.markdown_parser import parse_markdown, extract_sections
content = parse_markdown("examples/requirement_login.md")
sections = extract_sections(content)
for title, content in sections.items():
    print(f"## {title}")
    print(content[:100] + "...")
```

### 下午: 需求分析Agent
```python
# 文件: agents/requirement_analyzer.py
# 学习目标: 理解AI如何分析需求

# 练习1: 分析需求文档
from agents.requirement_analyzer import RequirementAnalyzer
from parsers.markdown_parser import parse_markdown

analyzer = RequirementAnalyzer()
requirement_text = parse_markdown("examples/requirement_login.md")
result = analyzer.analyze(requirement_text)

print("识别的需求数量:", len(result['requirements']))
for req in result['requirements']:
    print(f"- {req['id']}: {req['title']}")
```

## Day 3: 测试用例生成和评审

### 上午: 测试用例生成Agent
```python
# 文件: agents/test_case_generator.py
# 学习目标: 理解AI如何生成测试用例

# 练习: 生成测试用例
from agents.test_case_generator import TestCaseGenerator

generator = TestCaseGenerator()
requirement = {
    "id": "REQ_001",
    "title": "用户登录",
    "description": "用户可以通过用户名和密码登录",
    "acceptance_criteria": ["正确凭证可以登录", "错误凭证显示错误"]
}

test_cases = generator.generate(requirement)
print(f"生成了 {len(test_cases)} 个测试用例")
for tc in test_cases:
    print(f"- {tc['id']}: {tc['title']}")
```

### 下午: 测试用例评审Agent
```python
# 文件: agents/case_reviewer.py
# 学习目标: 理解AI如何评审测试用例质量

# 练习: 评审测试用例
from agents.case_reviewer import CaseReviewer

reviewer = CaseReviewer()
review_result = reviewer.review(requirement, test_cases)

print(f"评审结果: {'通过' if review_result['passed'] else '未通过'}")
print(f"评分: {review_result['score']}/100")
for comment in review_result['comments']:
    print(f"- {comment['message']}")
```

## Day 4: 自动化执行

### 上午: 脚本生成器
```python
# 文件: automation/midscene_generator.py
# 学习目标: 理解如何将测试用例转换为可执行脚本

# 练习: 生成Midscene脚本
from automation.midscene_generator import MidsceneScriptGenerator

generator = MidsceneScriptGenerator()
script_path = generator.generate(test_cases, page_url="https://example.com")
print(f"生成的脚本: {script_path}")

# 查看生成的脚本内容
with open(script_path, 'r', encoding='utf-8') as f:
    print(f.read()[:500] + "...")
```

### 下午: 测试执行和报告
```python
# 文件: automation/test_executor.py, automation/allure_reporter.py
# 学习目标: 理解测试执行和报告生成

# 练习1: 执行测试 (需要Playwright环境)
from automation.test_executor import TestExecutor

executor = TestExecutor()
result = executor.run_tests(script_path)
print(f"执行结果: {result['passed']}/{result['total']} 通过")

# 练习2: 生成报告
from automation.allure_reporter import AllureReporter

reporter = AllureReporter()
report_result = reporter.generate_report()
if report_result['status'] == 'success':
    print(f"报告已生成: {report_result['report_path']}")
```

## Day 5: 工作流编排

### 全天: LangGraph工作流
```python
# 文件: agents/workflow.py
# 学习目标: 理解多Agent协作机制

# 练习: 运行完整工作流
from agents.workflow import run_workflow

test_requirement = """
# 用户登录功能
用户可以通过用户名和密码登录系统。
验收标准:
1. 正确凭证可以登录
2. 错误凭证显示错误信息
"""

result = run_workflow(test_requirement, max_iterations=1)
print("工作流完成!")
print(f"- 需求数量: {len(result.get('requirements', []))}")
print(f"- 用例数量: {len(result.get('test_cases', []))}")
print(f"- 评审通过: {result.get('review_passed')}")
```