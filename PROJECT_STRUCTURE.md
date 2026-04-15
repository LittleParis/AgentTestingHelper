# AI测试自动化平台 - 项目结构

## 📁 目录结构

```
AI测试自动化平台/
├── 📁 core/                    # 核心模块
│   ├── agents/                 # Agent模块
│   │   ├── requirement_analyzer.py     # 需求分析Agent (已集成Pydantic)
│   │   ├── test_case_generator.py      # 测试用例生成Agent
│   │   ├── case_reviewer.py            # 测试用例评审Agent
│   │   └── workflow.py                 # LangGraph工作流编排
│   ├── models/                 # 数据模型 (Pydantic)
│   │   ├── requirement.py              # 需求相关模型
│   │   └── __init__.py
│   ├── parsers/               # 文档解析
│   │   └── markdown_parser.py
│   ├── automation/            # 自动化执行
│   │   ├── midscene_generator.py       # Midscene脚本生成
│   │   ├── test_executor.py            # 测试执行器
│   │   └── allure_reporter.py          # Allure报告生成
│   └── utils/                 # 工具模块
│       ├── llm_client.py               # LLM客户端封装
│       └── project_paths.py            # 项目路径管理
├── 📁 tests/                   # 测试目录
│   ├── unit/                  # 单元测试
│   │   ├── test_analyzer_core.py       # 需求分析Agent测试
│   │   ├── test_simple_pydantic.py     # Pydantic模型测试
│   │   └── ...
│   ├── integration/           # 集成测试
│   │   ├── test_main_flow.py           # 主流程集成测试
│   │   ├── test_workflow.py            # 工作流测试
│   │   └── ...
│   ├── fixtures/              # 测试数据
│   └── generated/             # 生成的测试脚本
├── 📁 docs/                    # 文档目录
│   ├── guides/                # 学习指南
│   │   └── learning_guide/             # 完整学习路线
│   ├── improvements/          # 改进建议
│   │   └── project_improvements/       # 项目改进文档
│   ├── api/                   # API文档
│   ├── PYDANTIC_IMPROVEMENT_SUMMARY.md # Pydantic改进总结
│   ├── QUICKSTART.md                   # 快速开始指南
│   └── PROJECT_STRUCTURE.md            # 项目结构说明
├── 📁 examples/               # 示例文件
│   └── requirement_*.md                # 需求文档示例
├── 📁 output/                 # 输出目录
│   ├── requirements*.json              # 需求分析结果
│   ├── test_cases*.json               # 生成的测试用例
│   └── review*.json                   # 评审结果
├── 📁 config/                 # 配置文件
│   ├── config.yaml                    # 项目配置
│   ├── pytest.ini                    # pytest配置
│   ├── playwright.config.ts           # Playwright配置
│   ├── package.json                   # Node.js依赖
│   └── tsconfig.json                  # TypeScript配置
├── 📁 scripts/                # 脚本工具
├── 📁 temp/                   # 临时文件
├── 📁 allure-results/         # Allure测试结果
├── 📁 allure-report/          # Allure测试报告
├── 📁 browsers/               # Playwright浏览器
├── 📁 node_modules/           # Node.js模块
├── 📁 .venv/                  # Python虚拟环境
├── 📁 .kiro/                  # Kiro配置
├── 📄 main.py                 # 主程序 (阶段1)
├── 📄 main_v2.py              # 主程序 (阶段2-3)
├── 📄 requirements.txt        # Python依赖
├── 📄 .env.example            # 环境变量模板
├── 📄 .gitignore              # Git忽略文件
└── 📄 README.md               # 项目说明
```

## 🎯 核心模块说明

### core/agents/ - Agent模块
- **requirement_analyzer.py**: 需求分析Agent，已集成Pydantic数据验证
- **test_case_generator.py**: 测试用例生成Agent
- **case_reviewer.py**: 测试用例评审Agent，支持LLM智能评审
- **workflow.py**: LangGraph工作流编排，支持多Agent协作

### core/models/ - 数据模型
- **requirement.py**: 需求相关的Pydantic模型
  - `Requirement`: 单个需求模型
  - `RequirementAnalysisResult`: 需求分析结果模型
  - 支持数据验证、类型安全、便捷方法

### core/automation/ - 自动化执行
- **midscene_generator.py**: 生成Midscene UI自动化脚本
- **test_executor.py**: 执行测试脚本并收集结果
- **allure_reporter.py**: 生成Allure测试报告

## 🧪 测试结构

### tests/unit/ - 单元测试
- 各个模块的独立功能测试
- Pydantic模型验证测试
- Agent核心逻辑测试

### tests/integration/ - 集成测试
- 端到端流程测试
- 多Agent协作测试
- 工作流集成测试

## 📚 文档结构

### docs/guides/ - 学习指南
- 完整的学习路线和教程
- 从入门到高级的分步指南

### docs/improvements/ - 改进建议
- 项目改进分析和建议
- Pydantic集成指南
- 功能增强计划

## ⚙️ 配置管理

所有配置文件统一放在 `config/` 目录：
- Python项目配置
- 测试框架配置
- 前端工具配置
- 依赖管理文件

## 🚀 使用方式

### 导入路径更新
```python
# 新的导入路径
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.requirement import Requirement, RequirementAnalysisResult
from core.utils.llm_client import get_llm_client
```

### 运行测试
```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 所有测试
pytest tests/
```

### 运行主程序
```bash
# 阶段2工作流 (推荐)
python main_v2.py

# 阶段1基础流程
python main.py
```

## 📋 整理效果

1. **结构清晰** - 核心模块、测试、文档分离
2. **易于维护** - 相关文件集中管理
3. **便于扩展** - 模块化设计，易于添加新功能
4. **规范统一** - 统一的目录命名和组织方式