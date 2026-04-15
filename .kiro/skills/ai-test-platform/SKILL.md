# AI 测试平台开发技能 (Kiro版)

## 🎯 技能概述

协助用户从零开始搭建一个完整的 AI 驱动的自动化测试平台，基于重构后的项目架构。

**关键词**: 测试平台, 自动化测试, 测试用例生成, UI自动化, pytest, midscene, Allure, LangGraph, Pydantic

**⚠️ 重要要求**：
1. **架构变动管理**：每次涉及架构变动时，必须同步更新技能文档中的架构描述
2. **虚拟环境运行**：所有操作必须在虚拟环境 (.venv) 中执行
3. **完整性验证**：每次更改后必须运行完整主流程确保功能正常

## 📁 项目架构 (当前版本: v2.3)

```
AI测试自动化平台/ (项目根目录)
├── 📁 core/                    # 核心模块 (重构后)
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
│   │   └── allure_reporter.py          # Allure报告生成 (已优化)
│   └── utils/                 # 工具模块
│       ├── llm_client.py               # LLM客户端封装
│       └── project_paths.py            # 项目路径管理
├── 📁 tests/                   # 测试目录
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   ├── fixtures/              # 测试数据
│   └── generated/             # 生成的测试脚本
├── 📁 docs/                    # 文档目录
│   ├── guides/                # 学习指南
│   ├── improvements/          # 改进建议
│   ├── retrospectives/        # 阶段复盘文档 (强制要求)
│   └── api/                   # API文档
├── 📁 examples/               # 示例文件
├── 📁 config/                 # 配置文件
│   └── playwright.config.ts           # Playwright配置 (已优化Allure集成)
├── 📁 scripts/                # 脚本工具
│   └── generate_allure_from_results.py # Allure降级生成脚本 (新增)
├── 📁 .venv/                  # 虚拟环境 (必须使用)
├── 📁 allure-results/         # Allure测试结果
├── 📁 allure-report/          # Allure HTML报告
├── 📁 midscene_run/           # Midscene执行目录
│   └── generated/             # 生成的Midscene测试脚本
├── 📄 main_v2.py              # 主程序 (LangGraph工作流) - 已优化报告生成
└── 📄 requirements.txt        # Python依赖
```

**架构变更历史**：
- v2.0: 引入模块化结构，core/ 目录集中核心功能
- v2.1: 集成 Pydantic 数据验证，增强类型安全
- v2.2: 项目结构重构，统一导入路径
- v2.3: 优化 Allure 报告生成，添加降级处理机制

## 🔄 开发工作流程 (强制要求)

### 1. 虚拟环境管理

**所有操作必须在虚拟环境中执行**：

```bash
# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source .venv/bin/activate

# 验证环境
python --version
pip list | findstr langchain  # Windows
pip list | grep langchain     # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 架构变动管理流程

**每次涉及架构变动时，必须按以下顺序执行**：

1. **更新项目架构**：修改代码结构、添加新模块等
2. **同步更新技能文档**：更新本文档中的项目架构部分
3. **更新版本号**：在架构描述中增加版本号和变更说明
4. **运行完整验证**：执行主流程确保功能正常
5. **创建复盘文档**：记录变更原因和影响

### 3. 完整性验证流程

**每次更改后必须执行的验证步骤**：

```bash
# 1. 激活虚拟环境
.venv\Scripts\activate

# 2. 运行主流程
python main_v2.py

# 3. 验证输出文件
ls output/
ls allure-results/
ls allure-report/

# 4. 检查报告生成
# 应该自动打开浏览器显示 Allure 报告
```

**验证成功标准**：
- ✅ 主流程完整执行无错误
- ✅ 生成需求分析、测试用例、评审结果
- ✅ 执行测试脚本 (即使失败也要有执行记录)
- ✅ 自动生成并打开 Allure 报告
- ✅ 所有输出文件正确生成

## 🚀 核心工作流

### 1. 需求文档分析 (已集成 Pydantic)

**新的导入路径**:
```python
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.requirement import Requirement, RequirementAnalysisResult
```

**使用方式**:
```python
analyzer = RequirementAnalyzer()

# 向后兼容的字典接口
result_dict = analyzer.analyze(requirement_text)

# 新的类型安全接口 (推荐)
result_model = analyzer.analyze_structured(requirement_text)

# 使用便捷方法
high_priority = result_model.get_requirements_by_priority(Priority.HIGH)
functional_reqs = result_model.get_requirements_by_type(RequirementType.FUNCTIONAL)
```

### 2. 测试用例生成

基于需求分析结果调用测试用例生成 Agent，输出结构化的测试用例JSON。

### 3. 测试用例评审

执行自动评审检查：覆盖率、重复性、可执行性、边界值、优先级合理性。

### 4. 自动化脚本生成

将测试用例转换为可执行的 pytest + midscene/playwright 脚本。

### 5. 测试执行与报告 (已优化)

**执行测试**:
```bash
# 在虚拟环境中执行
.venv\Scripts\activate

# 执行全部测试
pytest tests/generated/ --alluredir=allure-results

# 执行 P0 用例 (冒烟测试)
pytest tests/generated/ -m smoke --alluredir=allure-results
```

**生成 Allure 报告** (已集成降级处理):
```bash
# 主流程会自动处理，包含以下逻辑：
# 1. 检查 allure-results 目录
# 2. 如果为空，自动从执行结果生成 Allure 数据
# 3. 生成静态报告
# 4. 启动本地服务
# 5. 自动打开浏览器

# 手动生成 (如需要)
python scripts/generate_allure_from_results.py
allure generate allure-results -o allure-report --clean
```

## 🎯 运行命令 (虚拟环境)

**⚠️ 重要：所有命令必须在激活的虚拟环境中执行**

### 环境准备
```bash
# 1. 激活虚拟环境
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. 验证环境
python --version
pip list | findstr pydantic  # 应该显示 pydantic 版本

# 3. 如果依赖缺失，重新安装
pip install -r requirements.txt
```

### 主流程执行
```bash
# 激活环境后执行主流程
python main_v2.py

# 预期输出：
# [步骤0] 清理历史数据...
# [步骤1] 读取需求文档...
# [步骤2] 启动完整工作流...
# [步骤3] 保存结果...
# [步骤4] 打开测试报告...
# [OK] 已自动打开浏览器
```

### 测试和验证
```bash
# 测试 Pydantic 模型
python tests/unit/test_analyzer_core.py

# 运行单元测试
python -m pytest tests/unit/ -v

# 生成 Allure 报告 (手动)
python scripts/generate_allure_from_results.py
allure generate allure-results -o allure-report --clean
```

## ❓ 常见问题与解决方案

**Q: 生成的测试脚本无法运行？**
A: 阶段 1 生成的脚本是模板，需要手动调整选择器。阶段 2 会改进为更智能的生成。

**Q: API 调用失败？**
A: 检查 `.env` 文件中的 `LLM_KEY` 是否正确配置。

**Q: 导入路径错误？**
A: 项目重构后，所有核心模块都在 `core/` 目录下，使用 `from core.agents.xxx import xxx` 格式。

**Q: Pydantic 版本兼容性问题？**
A: 项目使用 Pydantic V2，注意使用 `pattern` 而不是 `regex`，`@field_validator` 而不是 `@validator`。

**Q: 虚拟环境相关问题？**
A: 
- 确保使用 `.venv\Scripts\activate` (Windows) 或 `source .venv/bin/activate` (Linux/Mac) 激活环境
- 检查 `python --version` 和 `pip list` 确认环境正确
- 如果依赖缺失，运行 `pip install -r requirements.txt`

**Q: Allure 报告生成失败？**
A: 
- 检查 `allure --version` 确认 Allure 已安装
- 主流程会自动处理空结果目录的情况
- 手动运行 `python scripts/generate_allure_from_results.py` 生成降级结果

**Q: 主流程执行失败？**
A: 
- 确保在虚拟环境中运行
- 检查 `.env` 文件配置
- 查看 `output/` 目录中的执行日志
- 运行 `python -c "from core.agents.workflow import run_workflow; print('工作流可用')"` 测试

## 🔄 复盘机制 (强制要求)

### 复盘原则

**核心要求**：每完成一个开发阶段或解决一个重要问题后，必须进行复盘并记录，避免重复犯错。

### 复盘时机

1. **阶段开始时** - 回顾上一阶段的复盘文档
2. **遇到问题并解决后** - 立即记录问题和解决方案
3. **阶段完成时** - 创建当前阶段的完整复盘文档
4. **项目里程碑** - 重要功能完成后的总结

### 复盘文档位置

```
docs/retrospectives/
├── README.md                    # 复盘索引
├── phase1-hello-world.md        # 阶段1复盘
├── phase2-agent-workflow.md     # 阶段2复盘
├── phase3.1-midscene-setup.md   # 阶段3.1复盘
├── pydantic-integration.md      # Pydantic集成复盘
├── project-restructure.md       # 项目重构复盘
└── common-issues.md             # 常见问题汇总
```

## 开发规范

1. **代码规范** - Python 代码遵循 PEP 8，使用类型注解
2. **测试策略** - 单元测试 + 集成测试 + 端到端测试
3. **文档维护** - 及时更新文档，记录重要决策
4. **复盘机制** - 强制执行问题解决记录和阶段复盘
5. **虚拟环境** - 所有操作必须在 .venv 中执行

## 学习资源

- [Pydantic V2 文档](https://docs.pydantic.dev/2.0/)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Midscene UI 自动化](https://midscenejs.com/)
- [Allure 报告框架](https://docs.qameta.io/allure/)
- [Playwright 文档](https://playwright.dev/python/)