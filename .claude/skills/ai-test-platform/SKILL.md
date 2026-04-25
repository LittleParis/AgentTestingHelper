---
name: ai-test-platform
description: AI 测试平台开发助手 - 基于重构后的项目架构，帮助搭建完整的自动化测试平台。当用户提到测试平台、自动化测试、测试用例生成、UI 自动化、pytest、midscene、Allure 或测试相关开发时使用此技能。
compatibility:
  - 工具：文件操作、Shell 命令执行
  - 依赖：pytest, midscene/playwright, allure-pytest, pydantic, langchain, langgraph, Python 3.10+
  - 环境：必须使用虚拟环境 (.venv) 运行
---

# AI 测试平台开发技能

## 🎯 技能目标

协助用户搭建 AI 驱动的自动化测试平台，核心功能包括：
- 需求分析 → 测试用例生成 → 用例评审 → Midscene UI 自动化 → Allure 报告

## 📁 项目架构 (v3.0)

```
AgentTest/ (项目根目录)
├── core/                        # 核心模块
│   ├── agents/                  # Agent 模块
│   │   ├── requirement_analyzer.py   # 需求分析 Agent
│   │   ├── test_case_generator.py    # 测试用例生成 Agent
│   │   ├── case_reviewer.py          # 测试用例评审 Agent
│   │   └── workflow.py               # LangGraph 工作流编排
│   ├── models/                  # Pydantic V2 数据模型
│   │   ├── requirement.py            # 需求模型
│   │   ├── test_case.py             # 测试用例模型
│   │   ├── review.py                # 评审模型
│   │   └── config.py                # 配置管理（单例）
│   ├── automation/              # 自动化执行
│   │   ├── midscene_generator.py    # Midscene 脚本生成（LLM 转换）
│   │   ├── test_executor.py         # 测试执行器
│   │   └── allure_reporter.py       # Allure 报告生成
│   ├── parsers/                 # 文档解析
│   │   └── markdown_parser.py
│   └── utils/                   # 工具模块
│       ├── llm_client.py            # LLM 客户端（重试+Token追踪+单例）
│       └── project_paths.py         # 项目路径管理
├── tests/                       # 测试目录
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
├── docs/                        # 文档目录
│   ├── fix-records/             # 修复记录
│   └── issues/                  # Issue 列表
├── examples/                    # 示例需求文档
├── config/                      # 配置文件
│   └── playwright.config.ts
├── midscene_run/                # Midscene 执行目录
│   └── generated/               # 生成的测试脚本
├── output/                      # 输出文件
├── allure-results/              # Allure 测试结果
├── main_v2.py                   # 主程序入口
└── requirements.txt             # Python 依赖
```

## 🔄 已完成功能

| Issue | 功能 | 状态 |
|-------|------|------|
| #1 | 结构化输出替换手动 JSON 解析 | ✅ |
| #2 | 评审反馈注入生成器（有效迭代） | ✅ |
| #7 | LLMClient 重试机制 + Token 追踪 + 单例 | ✅ |
| #8 | Midscene action 转换改用 LLM | ✅ |

## 🚀 核心工作流

### 1. 需求分析

```python
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.requirement import Requirement, RequirementAnalysisResult

analyzer = RequirementAnalyzer()
result = analyzer.analyze_structured(requirement_text)
# result 是 RequirementAnalysisResult Pydantic 模型
```

### 2. 测试用例生成

```python
from core.agents.test_case_generator import TestCaseGenerator

generator = TestCaseGenerator()
result = generator.generate_structured(requirement, improvement_hints=hints)
# improvement_hints: 评审反馈，用于迭代改进
```

### 3. 用例评审

```python
from core.agents.case_reviewer import CaseReviewer

reviewer = CaseReviewer()
result = reviewer.review_structured(requirement, test_cases)
# result.passed: 是否通过
# result.suggestions: 改进建议列表
```

### 4. Midscene 脚本生成

```python
from core.automation.midscene_generator import MidsceneScriptGenerator

generator = MidsceneScriptGenerator(use_llm=True)  # use_llm=True 使用 LLM 转换
filepath = generator.generate(test_cases, page_url)
```

### 5. 运行主流程

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行完整流程
python main_v2.py
```

## 🔧 配置

### 环境变量 (.env)

```bash
# LLM 配置（必填）
LLM_KEY=your_api_key_here
LLM_MODEL=gpt-3.5-turbo

# 可选
LLM_BASE_URL=https://api.openai.com/v1
```

### 配置管理

```python
from core.models import get_settings

settings = get_settings()  # 单例
api_key = settings.llm_api_key
model = settings.llm_model
max_tokens = settings.llm_max_tokens  # 默认 8192
```

## 📋 待处理 Issue

参见 `docs/issues/issue-02.md`，优先级排序：

**P0（高优先级）**：
- #9: TestExecutor 改用 JSON reporter
- #13: 删除损坏的 requirement_analyzer_v2.py
- #15: TestCase.title 不合理的数字开头限制
- #17: playwright.config.ts 重复字段

**P1（中优先级）**：
- #3: 并行 Agent（fan-out）
- #4: Tool Calling
- #5: Human-in-the-loop
- #10: 工作流可观测性

## 🛠️ 常用命令

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行主流程
python main_v2.py

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行特定测试
python -m pytest tests/unit/test_llm_client_retry.py -v

# 生成 Allure 报告
allure serve allure-results
```

## 📝 开发规范

### 1. 导入路径

所有核心模块使用 `core.` 前缀：
```python
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models import get_settings
from core.utils.llm_client import get_llm_client
```

### 2. Pydantic V2

项目使用 Pydantic V2，注意：
- 使用 `pattern` 而不是 `regex`
- 使用 `@field_validator` 而不是 `@validator`
- 使用 `model_dump()` / `model_dump_json()` 而不是 `dict()` / `json()`

### 3. LLM 客户端

使用单例模式：
```python
from core.utils.llm_client import get_llm_client

llm = get_llm_client()  # 单例
response = llm.chat_simple(prompt)

# 结构化输出
structured_llm = llm.with_structured_output(MyPydanticModel)
result = structured_llm.invoke(prompt)
```

### 4. 修复记录

单元测试通过后，在 `docs/fix-records/` 创建修复记录：
- 文件命名：`YYYY-MM-DD-issue-{编号}.md`
- 更新 `docs/fix-records/README.md` 索引

## ❓ 常见问题

**Q: 导入路径错误？**
A: 确保使用 `from core.xxx import xxx` 格式。

**Q: LLM 调用失败？**
A: 检查 `.env` 中的 `LLM_KEY` 配置。LLMClient 有自动重试机制。

**Q: 测试脚本生成质量差？**
A: 确保 `use_llm=True`，使用 LLM 转换 action。

**Q: JSON 解析失败？**
A: 已使用结构化输出，解析失败率大幅降低。如仍有问题，检查 `max_tokens` 是否足够（默认 8192）。

## 🔗 相关文档

- [修复记录](docs/fix-records/README.md)
- [Issue 列表](docs/issues/issue-02.md)
- [Git Push Skill](.claude/skills/git-push/SKILL.md)
- [Fix Record Skill](.claude/skills/fix-record/SKILL.md)
