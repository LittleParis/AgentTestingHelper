# AI测试自动化平台

AI驱动的端到端测试自动化平台，从需求文档自动生成测试用例并执行UI自动化测试。

## 核心流程

```
需求文档 → Agent分析 → 生成测试用例 → UI自动化 → Allure报告
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# ANTHROPIC_API_KEY=your_api_key_here
```

### 3. 运行阶段1演示

```bash
python main.py
```

这将：
1. 读取 `examples/requirement_login.md` 需求文档
2. 使用Agent分析需求
3. 生成测试用例（保存到 `output/test_cases.json`）
4. 生成Playwright测试脚本（保存到 `tests/generated/`）

### 4. 查看生成的内容

```bash
# 查看需求分析结果
cat output/requirements.json

# 查看测试用例
cat output/test_cases.json

# 查看生成的测试脚本
ls tests/generated/
```

### 5. 运行测试（可选）

```bash
# 运行生成的测试
pytest tests/generated/ --alluredir=allure-results

# 查看Allure报告
allure serve allure-results
```

## 项目结构

```
.
├── agents/              # Agent模块
│   ├── requirement_analyzer.py    # 需求分析Agent
│   └── test_case_generator.py    # 测试用例生成Agent
├── parsers/            # 文档解析
│   └── markdown_parser.py
├── automation/         # 自动化执行
│   └── script_generator.py
├── examples/           # 示例需求文档
│   └── requirement_login.md
├── output/             # 输出目录
├── tests/              # 测试目录
│   └── generated/      # 生成的测试脚本
├── .kiro/              # Kiro配置
│   ├── steering/       # 项目规范
│   └── skills/         # 技能库
├── main.py             # 主程序
├── config.yaml         # 配置文件
└── requirements.txt    # 依赖列表
```

## 学习路线

### ✅ 阶段1：Hello World（当前）
- [x] 基础项目结构
- [x] 需求分析Agent
- [x] 测试用例生成Agent
- [x] 脚本生成器
- [x] 端到端流程演示

### 🔄 阶段2：Agent化（下一步）
- [ ] 引入LangGraph状态机
- [ ] 实现工作流编排
- [ ] 添加Tool Calling
- [ ] 优化Prompt

### 📋 阶段3：工程化
- [ ] 数据库集成（PostgreSQL）
- [ ] 版本管理
- [ ] API接口

### 🧠 阶段4：智能化
- [ ] 测试策略Agent
- [ ] 失败分析Agent
- [ ] 用例优化

### 🎨 阶段5：前端界面
- [ ] React前端
- [ ] 文档上传
- [ ] 报告展示

## 技术栈

- **Agent框架**: LangGraph（阶段2引入）
- **LLM**: Claude 3.5 Sonnet
- **文档解析**: PyMuPDF, python-docx
- **UI自动化**: Playwright（Midscene概念验证）
- **测试报告**: Allure Framework
- **数据存储**: PostgreSQL（阶段3引入）

## 开发指南

### 添加新的需求文档

在 `examples/` 目录创建Markdown文件：

```markdown
# 功能标题

## 功能描述
描述功能...

## 详细需求
详细说明...

## 验收标准
1. 标准1
2. 标准2
```

### 自定义Agent行为

编辑 `.kiro/steering/` 中的规则文件来调整Agent行为。

### 查看技能库

查看 `.kiro/skills/` 了解各个模块的最佳实践。

## 常见问题

### Q: 生成的测试脚本无法运行？
A: 阶段1生成的脚本是模板，需要手动调整选择器。阶段2会改进为更智能的生成。

### Q: API调用失败？
A: 检查 `.env` 文件中的 `ANTHROPIC_API_KEY` 是否正确配置。

### Q: 如何调整生成的测试用例？
A: 修改 `agents/test_case_generator.py` 中的prompt模板。

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT
