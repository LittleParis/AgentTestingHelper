---
inclusion: always
---

# AI 测试自动化项目上下文

> **注意**: 本项目主要使用 Claude Code 作为 AI 助手，全局 skill 位于 `~/.claude/skills/ai-test-platform/`

## 项目概述
这是一个 AI 驱动的端到端测试自动化平台，核心流程：
用户提交需求文档 → Agent 分析需求 → Agent 生成测试用例 → Midscene UI 自动化 → Allure 报告输出

## 技术栈
- **AI 助手**: Claude Code (主要使用)
- **LLM**: 通义千问 qwen-coder-plus (阿里云百炼)
- **文档解析**: Markdown, PyMuPDF, python-docx
- **UI 自动化**: Playwright / Midscene
- **测试框架**: pytest
- **测试报告**: Allure Framework
- **数据存储**: PostgreSQL (阶段 3 引入)
- **前端界面**: React (阶段 5 引入)

## 项目结构
```
G:\桌面\AgentTest/
├── agents/              # Agent 模块
│   ├── requirement_analyzer.py    # 需求分析 Agent
│   └── test_case_generator.py    # 测试用例生成 Agent
├── parsers/            # 文档解析
│   └── markdown_parser.py
├── automation/         # 自动化执行
│   └── script_generator.py
├── tests/              # 测试目录
│   ├── conftest.py
│   └── generated/      # 生成的测试脚本
├── examples/           # 示例需求文档
├── output/             # 输出目录
├── utils/
│   └── llm_client.py   # LLM 客户端
├── config.yaml         # 配置文件
├── main.py             # 主程序
└── .kiro/              # Kiro 配置 (保留作为项目文档)
    └── steering/       # 项目规范
```

## 当前阶段

### ✅ 阶段 1：Hello World (当前)
- [x] 基础项目结构
- [x] 需求分析 Agent
- [x] 测试用例生成 Agent
- [x] 脚本生成器
- [x] 端到端流程演示

### 🔄 阶段 2：Agent 化 (下一步)
- [ ] 引入 LangGraph 状态机
- [ ] 实现工作流编排
- [ ] 添加 Tool Calling
- [ ] 优化 Prompt

## 代码规范
- Python 代码遵循 PEP 8
- 使用类型注解（Type Hints）
- 函数和类必须有 docstring
- 配置文件使用 YAML 格式
- 敏感信息使用环境变量

## 开发原则
- Agent 决策过程要可追溯（记录思考链）
- 失败要有详细日志和截图
- 支持人工审核关键节点
- 成本控制：缓存 LLM 响应，避免重复调用
- 模块化设计：每个 Agent 独立可测试
