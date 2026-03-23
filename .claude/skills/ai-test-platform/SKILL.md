---
name: ai-test-platform
description: AI 测试平台开发助手 - 基于 G:\桌面\AgentTest 项目架构，帮助搭建完整的自动化测试平台，包括需求分析、测试用例生成、用例评审、midscene UI 自动化执行、pytest 框架管理和 Allure 报告导出。当用户提到测试平台、自动化测试、测试用例生成、UI 自动化、pytest、midscene、Allure 或测试相关开发时使用此技能。
compatibility:
  - 工具：文件操作、Shell 命令执行
  - 依赖：pytest, midscene/playwright, allure-pytest, Python 3.8+
---

# AI 测试平台开发技能

## 技能目标

协助用户从零开始搭建一个完整的 AI 驱动的自动化测试平台，基于以下项目架构：

```
AgentTest/
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
├── output/             # 输出目录 (需求分析结果、测试用例)
├── allure-results/     # Allure 结果目录
├── .kiro/              # Kiro 配置
│   ├── steering/       # 项目规范
│   └── skills/         # 技能库
├── utils/
│   └── llm_client.py   # LLM 客户端 (支持阿里云百炼)
├── config.yaml         # 配置文件
├── main.py             # 主程序
└── requirements.txt    # 依赖列表
```

## 核心工作流

### 第一阶段：需求文档分析

当用户提供需求文档后：

1. **读取需求文档** - 支持 Markdown、PDF、Word 格式
2. **调用需求分析 Agent** - 使用 LLM (通义千问/百炼) 分析需求
3. **输出结构化需求** - JSON 格式包含：
   - 功能模块清单
   - 需求优先级
   - 验收标准
   - UI 元素列表

**需求分析 Agent 输出格式**:
```json
{
  "requirements": [
    {
      "id": "REQ_001",
      "title": "需求标题",
      "description": "详细描述",
      "priority": "high",
      "type": "functional",
      "acceptance_criteria": ["验收标准 1", "验收标准 2"],
      "ui_elements": ["涉及的 UI 元素"]
    }
  ],
  "summary": "需求概述"
}
```

### 第二阶段：测试用例生成

基于需求分析结果调用测试用例生成 Agent：

1. **为每个需求生成测试用例** - 包含正向和负向测试
2. **输出格式**:
```json
{
  "test_cases": [
    {
      "id": "TC_LOGIN_001",
      "requirement_id": "REQ_LOGIN_001",
      "title": "用户正常登录",
      "priority": "high",
      "type": "functional",
      "steps": [
        {
          "step_number": 1,
          "action": "打开登录页面",
          "data": "https://example.com/login",
          "expected": "显示登录表单"
        },
        {
          "step_number": 2,
          "action": "输入用户名",
          "data": "test@example.com",
          "expected": "输入框显示输入内容"
        }
      ],
      "expected": "登录成功，跳转到首页",
      "tags": ["smoke", "login"]
    }
  ]
}
```

### 第三阶段：测试用例评审

执行自动评审检查：

1. **覆盖率检查** - 确保所有需求点都有对应用例
2. **重复性检查** - 识别重复或高度相似的用例
3. **可执行性检查** - 验证步骤描述是否可被自动化执行
4. **边界值检查** - 确认包含边界条件和异常场景
5. **优先级合理性** - 审查 P0 用例是否为核心场景

**评审报告输出**:
- 用例总数统计
- 覆盖率分析 (需求->用例映射)
- 问题清单及修改建议
- 评审结论 (通过/需修改/不通过)

### 第四阶段：自动化脚本生成

将测试用例转换为可执行的 pytest + midscene/playwright 脚本：

**生成的脚本结构**:
```python
"""
测试用例：用户正常登录
ID: TC_LOGIN_001
优先级：high
"""
import pytest
import allure
from playwright.async_api import Page, expect


@allure.title("用户正常登录")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
async def test_tc_login_001(page: Page):
    """
    测试用例 ID: TC_LOGIN_001
    需求 ID: REQ_LOGIN_001
    """
    try:
        with allure.step("步骤 1: 打开登录页面"):
            await page.goto("https://example.com/login")
            allure.attach(
                await page.screenshot(),
                name="登录页面",
                attachment_type=allure.attachment_type.PNG
            )

        with allure.step("步骤 2: 输入用户名"):
            await page.fill('input[name="email"]', "test@example.com")

        with allure.step("步骤 3: 输入密码"):
            await page.fill('input[name="password"]', "password123")

        with allure.step("步骤 4: 点击登录按钮"):
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")

        with allure.step("验证：登录成功"):
            await expect(page).to_contain_text("欢迎回来")
            allure.attach(
                await page.screenshot(),
                name="登录成功",
                attachment_type=allure.attachment_type.PNG
            )

    except Exception as e:
        allure.attach(str(e), name="错误信息", attachment_type=allure.attachment_type.TEXT)
        allure.attach(
            await page.screenshot(),
            name="失败截图",
            attachment_type=allure.attachment_type.PNG
        )
        raise
```

### 第五阶段：测试执行与报告

**执行测试**:
```bash
# 执行全部测试
pytest tests/generated/ --alluredir=allure-results

# 执行 P0 用例 (冒烟测试)
pytest tests/generated/ -m smoke --alluredir=allure-results

# 并行执行
pytest tests/generated/ -n auto --alluredir=allure-results

# 失败重试
pytest tests/generated/ --reruns 2 --alluredir=allure-results
```

**生成 Allure 报告**:
```bash
# 生成静态报告
allure generate allure-results -o allure-report --clean

# 快速预览
allure serve allure-results
```

## 配置模板

### config.yaml
```yaml
project:
  name: "AI 测试自动化平台"
  version: "0.1.0"

llm:
  model: "qwen-coder-plus"  # 通义千问编程版
  temperature: 0.7
  max_tokens: 4096

testing:
  screenshot_on_failure: true
  video_on_failure: false
  retry_times: 2
  timeout: 30000

reporting:
  allure_results_dir: "allure-results"
  screenshots_dir: "screenshots"
```

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --alluredir=allure-results
    --strict-markers
markers =
    p0: P0 优先级用例
    p1: P1 优先级用例
    p2: P2 优先级用例
    smoke: 冒烟测试
    regression: 回归测试
```

### conftest.py
```python
import pytest
import allure
from playwright.async_api import async_playwright


@pytest.fixture(scope="session")
def browser():
    """创建浏览器实例"""
    import asyncio

    async def _setup():
        playwright = await async_playwright.start()
        browser = await playwright.chromium.launch(headless=True)
        return browser

    browser = asyncio.get_event_loop().run_until_complete(_setup())
    yield browser
    asyncio.get_event_loop().run_until_complete(browser.close())


@pytest.fixture(scope="function")
async def page(browser):
    """创建页面实例"""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )
    page = await context.new_page()
    yield page
    await page.close()
    await context.close()
```

### .env.example
```bash
# 阿里云百炼 API 密钥
DASHSCOPE_API_KEY=your_api_key_here

# LLM 模型选择
LLM_MODEL=qwen-coder-plus
```

## Midscene UI 自动化规范

### AI 视觉定位
```python
from midscene import Page, expect

async def test_ai_login():
    page = Page()

    # 使用 AI 视觉定位执行操作
    await page.goto("https://example.com/login")
    await page.ai_action("在邮箱输入框输入", text="test@example.com")
    await page.ai_action("在密码输入框输入", text="password123")
    await page.ai_action("点击登录按钮")

    # AI 驱动断言
    result = await page.ai_query("页面是否显示欢迎消息")
    assert result, "登录失败"

    await page.close()
```

### 页面对象模式
```python
from dataclasses import dataclass

@dataclass
class LoginPage:
    page: Page
    url: str = "https://example.com/login"

    async def navigate(self):
        await self.page.goto(self.url)

    async def login(self, email: str, password: str):
        await self.page.ai_action("在邮箱输入框输入", text=email)
        await self.page.ai_action("在密码输入框输入", text=password)
        await self.page.ai_action("点击登录按钮")

    async def is_logged_in(self) -> bool:
        return await self.page.ai_query("页面是否显示用户头像")
```

## Allure 报告集成

### 装饰器使用
```python
import allure

@allure.feature("用户管理")
@allure.story("用户登录")
@allure.title("测试正常登录流程")
@allure.description("验证用户使用正确的邮箱和密码能够成功登录")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("smoke", "login")
@allure.link("https://jira.com/ISSUE-123", name="需求链接")
async def test_normal_login():
    pass
```

### 步骤记录
```python
@allure.step("打开登录页面")
async def open_login_page(page):
    await page.goto("https://example.com/login")

@allure.step("输入用户凭证：{email}")
async def enter_credentials(page, email: str, password: str):
    await page.fill('input[name="email"]', email)
    await page.fill('input[name="password"]', password)

# 使用
async def test_login():
    await open_login_page(page)
    await enter_credentials(page, "test@example.com", "password")
```

## LLM 集成 (阿里云百炼)

### LLMClient 使用
```python
from utils.llm_client import get_llm_client

# 获取客户端
llm = get_llm_client()

# 简单调用
response = llm.chat_simple("分析以下需求文档...")

# 带参数调用
response = llm.chat(
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    max_tokens=4096
)
```

## 开发指南

### 添加新的需求文档
在 `examples/` 目录创建 Markdown 文件：
```markdown
# 功能标题

## 功能描述
描述功能...

## 详细需求
详细说明...

## 验收标准
1. 标准 1
2. 标准 2
```

### 运行主流程
```bash
# 执行完整流程
python main.py

# 查看生成的内容
cat output/requirements.json
cat output/test_cases.json
ls tests/generated/
```

### 自定义 Agent 行为
编辑 `.kiro/steering/` 中的规则文件来调整 Agent 行为：
- `test-automation-standards.md` - 测试自动化开发标准
- `prompt-templates.md` - Prompt 模板
- `agent-development.md` - Agent 开发指南

## 最佳实践

1. **用例设计** - 遵循 FIRST 原则 (Fast, Independent, Repeatable, Self-validating, Timely)
2. **选择器策略** - 优先使用 data-testid，其次 id/class，AI 视觉定位作为补充
3. **数据管理** - 测试数据与脚本分离，使用 fixture 或 YAML/JSON 管理
4. **错误处理** - 添加显式等待，避免硬编码 sleep
5. **报告优化** - 使用 Allure 的@allure.step、@allure.attachment 增强报告可读性

## 学习路线

### 阶段 1：Hello World (当前)
- [x] 基础项目结构
- [x] 需求分析 Agent
- [x] 测试用例生成 Agent
- [x] 脚本生成器
- [x] 端到端流程演示

### 阶段 2：Agent 化 (下一步)
- [ ] 引入 LangGraph 状态机
- [ ] 实现工作流编排
- [ ] 添加 Tool Calling
- [ ] 优化 Prompt

### 阶段 3：工程化
- [ ] 数据库集成 (PostgreSQL)
- [ ] 版本管理
- [ ] API 接口

### 阶段 4：智能化
- [ ] 测试策略 Agent
- [ ] 失败分析 Agent
- [ ] 用例优化

### 阶段 5：前端界面
- [ ] React 前端
- [ ] 文档上传
- [ ] 报告展示

## 常见问题

**Q: 生成的测试脚本无法运行？**
A: 阶段 1 生成的脚本是模板，需要手动调整选择器。阶段 2 会改进为更智能的生成。

**Q: API 调用失败？**
A: 检查 `.env` 文件中的 `DASHSCOPE_API_KEY` 是否正确配置。

**Q: 如何调整生成的测试用例？**
A: 修改 `agents/test_case_generator.py` 中的 prompt 模板。

**Q: 如何查看 Allure 报告？**
A: 运行 `allure serve allure-results` 在浏览器中查看报告。
