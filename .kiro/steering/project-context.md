---
inclusion: always
---

# AI测试自动化项目上下文

## 项目概述
这是一个AI驱动的端到端测试自动化平台，核心流程：
用户提交需求文档 → Agent分析需求 → Agent生成测试用例 → Midscene UI自动化 → Allure报告输出

## 技术栈
- **Agent框架**: LangGraph (状态管理清晰，适合复杂工作流)
- **LLM**: Claude 3.5 Sonnet (推理能力强)
- **文档解析**: PyMuPDF, python-docx, unstructured
- **UI自动化**: Midscene + Playwright
- **测试报告**: Allure Framework
- **数据存储**: PostgreSQL (需求/用例版本管理)
- **任务队列**: Redis + Celery (异步任务处理)
- **前端界面**: React + Ant Design

## 项目结构
```
project/
├── agents/              # Agent模块
│   ├── requirement_analyzer.py    # 需求分析Agent
│   ├── test_case_generator.py    # 测试用例生成Agent
│   ├── test_strategy.py          # 测试策略Agent
│   └── failure_analyzer.py       # 失败分析Agent
├── automation/          # 自动化执行
│   ├── midscene_runner.py        # Midscene执行器
│   └── script_templates/         # 脚本模板
├── parsers/            # 文档解析
│   ├── pdf_parser.py
│   ├── docx_parser.py
│   └── markdown_parser.py
├── models/             # 数据模型
│   ├── requirement.py
│   └── test_case.py
├── reports/            # 报告生成
│   └── allure_integration.py
├── api/                # API接口
│   └── main.py
├── web/                # 前端界面
└── tests/              # 单元测试
```

## 核心Agent设计

### 1. 需求分析Agent
- 输入：需求文档（PDF/Word/Markdown）
- 输出：结构化需求JSON（功能点、优先级、依赖关系）
- 能力：文档理解、信息提取、需求分类

### 2. 测试用例生成Agent
- 输入：结构化需求
- 输出：测试用例集（包含步骤、预期结果、测试数据）
- 能力：边界值分析、等价类划分、场景组合

### 3. 测试策略Agent
- 输入：需求 + 历史数据
- 输出：测试计划、优先级排序
- 能力：风险评估、覆盖率分析

### 4. 失败分析Agent
- 输入：失败的测试结果
- 输出：根因分析、修复建议
- 能力：日志分析、模式识别

## 代码规范
- Python代码遵循PEP 8
- 使用类型注解（Type Hints）
- 函数和类必须有docstring
- Agent的prompt模板统一放在`prompts/`目录
- 配置文件使用YAML格式
- 敏感信息使用环境变量

## 测试用例格式标准
```json
{
  "id": "TC001",
  "title": "用户登录-正常流程",
  "priority": "high",
  "type": "functional",
  "steps": [
    {"action": "打开登录页面", "data": "https://example.com/login"},
    {"action": "输入用户名", "data": "test@example.com"},
    {"action": "输入密码", "data": "password123"},
    {"action": "点击登录按钮"}
  ],
  "expected": "成功跳转到首页，显示用户名",
  "test_data": {...},
  "tags": ["login", "smoke"]
}
```

## 开发原则
- Agent决策过程要可追溯（记录思考链）
- 失败要有详细日志和截图
- 支持人工审核关键节点
- 成本控制：缓存LLM响应，避免重复调用
- 模块化设计：每个Agent独立可测试
