# AI 测试自动化平台

AI 驱动的端到端测试自动化平台，从需求文档自动生成测试用例并执行 UI 自动化测试。

## 核心流程

```
需求文档 → Agent 分析需求 → 生成测试用例 → LLM 评审 → Midscene UI 自动化 → Allure 报告
```

## 当前版本：v2.5（阶段3完成）

### 已实现功能

- **需求分析 Agent** — 解析 Markdown/PDF/Word 需求文档，输出结构化需求（Pydantic 验证）
- **测试用例生成 Agent** — 基于需求自动生成覆盖正向/负向/边界场景的测试用例
- **LLM 智能评审 Agent** — 5 维度评分（完整性/覆盖率/合理性/独立性/清晰度），评审不通过自动带反馈重试
- **Midscene 脚本生成** — 将测试用例转换为 Midscene + Playwright TypeScript 脚本，AI 自然语言定位元素
- **测试执行** — 自动执行生成的脚本，收集执行结果
- **Allure 报告** — 自动生成并打开 HTML 测试报告
- **LangGraph 工作流** — 多 Agent 协作，支持评审反馈迭代循环
- **结构化输出** — 所有 Agent 使用 `with_structured_output` 直接返回 Pydantic 模型

---

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Node.js 依赖（Midscene + Playwright）
npm install

# 安装 Playwright 浏览器
npx playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制模板
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Python Agent 使用的 LLM（需求分析、用例生成、评审）
LLM_KEY=your_api_key_here
LLM_MODEL=qwen-plus              # 或 gpt-4、deepseek-chat 等
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 可选

# Midscene UI 自动化使用的视觉模型
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max  # 需要支持视觉的模型
```

### 3. 运行完整流程

```bash
# 推荐：LangGraph 工作流（阶段3，包含 Midscene 执行）
python main_v2.py

# 基础流程（阶段1，仅生成脚本不执行）
python main.py
```

`main_v2.py` 执行步骤：
1. 读取 `examples/requirement_baidu.md` 需求文档
2. 需求分析 Agent 提取结构化需求
3. 测试用例生成 Agent 生成用例（带评审反馈迭代）
4. LLM 评审 Agent 5 维度评分
5. 生成 Midscene TypeScript 测试脚本
6. 执行测试脚本，收集结果
7. 生成 Allure HTML 报告并自动打开浏览器

### 4. 查看输出

```bash
output/
├── requirements(时间戳).json    # 需求分析结果
├── test_cases(时间戳).json      # 生成的测试用例
├── review(时间戳).json          # 评审结果和改进建议
└── execution(时间戳).json       # 测试执行结果

midscene_run/generated/          # 生成的 TypeScript 测试脚本
allure-report/                   # Allure HTML 报告
```

---

## 项目结构

```
AI测试自动化平台/
├── 📁 core/                         # 核心模块
│   ├── agents/                      # Agent 模块
│   │   ├── requirement_analyzer.py  # 需求分析 Agent（结构化输出）
│   │   ├── test_case_generator.py   # 测试用例生成 Agent（支持评审反馈）
│   │   ├── case_reviewer.py         # 测试用例评审 Agent（5维度评分）
│   │   └── workflow.py              # LangGraph 工作流编排
│   ├── models/                      # Pydantic 数据模型
│   │   ├── requirement.py           # 需求模型
│   │   ├── test_case.py             # 测试用例模型
│   │   ├── review.py                # 评审结果模型
│   │   └── config.py                # 配置管理（从 .env 读取）
│   ├── parsers/                     # 文档解析
│   │   └── markdown_parser.py
│   ├── automation/                  # 自动化执行
│   │   ├── midscene_generator.py    # Midscene 脚本生成器
│   │   ├── test_executor.py         # 测试执行器（调用 Playwright）
│   │   └── allure_reporter.py       # Allure 报告生成
│   └── utils/
│       ├── llm_client.py            # LLM 客户端封装（LangChain）
│       └── project_paths.py         # 项目路径常量
├── 📁 tests/
│   ├── unit/                        # 单元测试（15个测试文件）
│   └── integration/                 # 集成测试（5个测试文件）
├── 📁 midscene_run/
│   └── generated/                   # 生成的 TypeScript 测试脚本
├── 📁 docs/
│   ├── improvements/                # 优化设计文档
│   │   ├── agent_reasoning_design.md    # Agent 推理模式设计
│   │   ├── parallel_execution_design.md # 并行执行设计
│   │   └── rag_design.md               # RAG 知识库设计
│   └── retrospectives/              # 阶段复盘文档
├── 📁 examples/                     # 示例需求文档
│   ├── requirement_login.md         # 登录功能需求
│   └── requirement_baidu.md         # 百度搜索需求
├── 📁 output/                       # 运行输出（自动生成）
├── 📄 main_v2.py                    # 主程序入口（推荐）
├── 📄 main.py                       # 阶段1入口（基础流程）
├── 📄 requirements.txt              # Python 依赖
├── 📄 package.json                  # Node.js 依赖
└── 📄 playwright.config.ts          # Playwright 配置
```

---

## 开发路线图

### ✅ 阶段 1：Hello World（已完成）
- [x] 基础项目结构
- [x] 需求分析 Agent
- [x] 测试用例生成 Agent
- [x] Midscene 脚本生成器
- [x] 端到端流程演示

### ✅ 阶段 2：Agent 化（已完成）
- [x] 引入 LangGraph 状态机
- [x] 实现工作流编排（需求分析 → 用例生成 → 评审 → 反馈循环）
- [x] LLM 智能评审 Agent（5 维度评分）
- [x] 评审不通过自动带反馈迭代重试
- [x] Pydantic 数据验证（全 Agent 覆盖）
- [x] 结构化输出（`with_structured_output`）

### ✅ 阶段 3：Midscene 集成（已完成）
- [x] Midscene + Playwright 脚本生成
- [x] 测试执行器（调用 npx playwright test）
- [x] Allure 报告生成与自动打开
- [x] 执行失败兜底结果写入

### 🔧 当前：Bug 修复与工程化（进行中）
- [ ] 修复 45 个已知问题（见 `docs/improvements/`）
- [ ] 补全缺失依赖（langgraph、pydantic-settings）
- [ ] 修复 package.json 路径问题
- [ ] 统一日志系统（替换 print）
- [ ] 补充单元测试

### 📋 下一阶段：性能与智能化
- [ ] **并行执行**：asyncio 并发生成/评审，节省 60%+ 时间（见 `docs/improvements/parallel_execution_design.md`）
- [ ] **ReAct 推理**：CaseReviewer 升级为工具调用模式（见 `docs/improvements/agent_reasoning_design.md`）
- [ ] **RAG 知识库**：历史用例向量化，提升生成质量（见 `docs/improvements/rag_design.md`）
- [ ] **失败分析 Agent**：测试失败后 AI 自动分析原因
- [ ] **REST API**：FastAPI 接口层，支持外部集成
- [ ] **前端界面**：React + 实时进度推送

---

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| Agent 框架 | LangGraph | 工作流编排、状态管理 |
| LLM 集成 | LangChain + ChatOpenAI | 支持 OpenAI/阿里云/DeepSeek 等 |
| 数据验证 | Pydantic V2 | 所有 Agent 输入输出验证 |
| UI 自动化 | Midscene + Playwright | AI 自然语言定位元素 |
| 测试报告 | Allure Framework | HTML 报告，支持截图附件 |
| 文档解析 | Markdown（内置） | 后续扩展 PDF/Word |

---

## 常见问题

**Q: API 调用失败？**
检查 `.env` 文件中的 `LLM_KEY` 是否正确，`LLM_BASE_URL` 是否与服务商匹配。

**Q: Midscene 执行失败？**
确认 `OPENAI_API_KEY` 和 `MIDSCENE_MODEL_NAME` 已配置，且模型支持视觉能力（如 `qwen-vl-max`、`gpt-4o`）。

**Q: npx playwright test 找不到配置？**
确认项目根目录有 `playwright.config.ts`（不是 `config/` 子目录）。

**Q: 评审不通过会怎样？**
工作流最多迭代 2 次，每次会把评审建议注入生成器 prompt，第二次生成质量会更高。

**Q: 如何换一个需求文档？**
修改 `main_v2.py` 中的 `requirement_file` 路径和 `page_url`，或者等命令行参数功能实现后用 `--requirement` 参数指定。

---

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT
