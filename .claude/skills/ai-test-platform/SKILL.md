---
name: ai-test-platform
description: AI 测试平台开发助手 - 基于重构后的项目架构，帮助搭建完整的自动化测试平台。包括需求分析、测试用例生成、用例评审、midscene UI 自动化执行、pytest 框架管理和 Allure 报告导出。集成 Pydantic 数据验证，支持 LangGraph 工作流编排。当用户提到测试平台、自动化测试、测试用例生成、UI 自动化、pytest、midscene、Allure 或测试相关开发时使用此技能。
compatibility:
  - 工具：文件操作、Shell 命令执行
  - 依赖：pytest, midscene/playwright, allure-pytest, pydantic, langchain, langgraph, Python 3.8+
  - 环境：必须使用虚拟环境 (.venv) 运行
---

# AI 测试平台开发技能

## 🎯 技能目标

协助用户从零开始搭建一个完整的 AI 驱动的自动化测试平台，基于重构后的项目架构。

**⚠️ 重要要求**：
1. **架构变动管理**：每次涉及架构变动时，必须同步更新本技能文档中的架构描述
2. **虚拟环境运行**：所有操作必须在虚拟环境 (.venv) 中执行
3. **完整性验证**：每次更改后必须运行完整主流程确保功能正常

## 📁 项目架构 (当前版本: v2.5)

```
AI测试自动化平台/ (项目根目录)
├── 📁 core/                    # 核心模块 (重构后)
│   ├── agents/                 # Agent模块
│   │   ├── requirement_analyzer.py     # 需求分析Agent (已集成Pydantic)
│   │   ├── test_case_generator.py      # 测试用例生成Agent (已集成Pydantic)
│   │   ├── case_reviewer.py            # 测试用例评审Agent (已集成Pydantic)
│   │   └── workflow.py                 # LangGraph工作流编排
│   ├── models/                 # 数据模型 (Pydantic V2)
│   │   ├── requirement.py              # 需求相关模型
│   │   ├── test_case.py                # 测试用例模型
│   │   ├── review.py                   # 评审相关模型
│   │   ├── config.py                   # 配置管理模型 (V2升级)
│   │   └── __init__.py
│   ├── parsers/               # 文档解析
│   │   └── markdown_parser.py
│   ├── automation/            # 自动化执行
│   │   ├── midscene_generator.py       # Midscene脚本生成
│   │   ├── test_executor.py            # 测试执行器
│   │   └── allure_reporter.py          # Allure报告生成 (已优化)
│   └── utils/                 # 工具模块
│       ├── llm_client.py               # LLM客户端封装 (Pydantic响应模型)
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
- v2.4: Agent 全面 Pydantic 化，新增 review.py 模型文件
- v2.5: 配置管理升级 Pydantic V2，LLM 响应模型 Pydantic 化，统一配置使用

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

**架构变动检查清单**：
- [ ] 新增/删除/移动了核心模块
- [ ] 修改了导入路径
- [ ] 更改了配置文件结构
- [ ] 添加了新的依赖
- [ ] 修改了主流程逻辑

### 2.1 模块/功能新增记录 (强制要求)

**每次新增模块或功能时，必须在复盘文档中详细记录实现方式**：

**记录内容要求**：

1. **功能概述**：新增模块/功能的名称和用途
2. **实现方式**：
   - 核心代码结构
   - 关键类/函数设计
   - 数据流转过程
3. **依赖关系**：与其他模块的交互
4. **配置要求**：环境变量、配置文件等
5. **使用示例**：代码调用示例

**记录模板**：

```markdown
## 新增模块：[模块名称]

### 功能概述
[简要描述模块功能和用途]

### 实现方式

#### 核心代码结构
- 文件路径：`core/xxx/xxx.py`
- 主要类/函数：
  - `ClassName`：[说明]
  - `function_name()`：[说明]

#### 关键设计
[代码示例或设计说明]

#### 数据流转
1. 输入：[输入数据来源和格式]
2. 处理：[处理逻辑]
3. 输出：[输出数据格式和去向]

### 依赖关系
- 依赖模块：[列表]
- 被依赖：[列表]

### 配置要求
- 环境变量：[列表]
- 配置文件：[说明]

### 使用示例
\`\`\`python
from core.xxx import ClassName

# 使用示例代码
instance = ClassName()
result = instance.method()
\`\`\`
```

**示例记录**（参考阶段3.7）：

```markdown
## 新增模块：统一配置管理

### 功能概述
提供统一的配置管理入口，支持从 .env 文件读取配置，
使用 Pydantic V2 进行数据验证，单例模式避免重复读取。

### 实现方式

#### 核心代码结构
- 文件路径：`core/models/config.py`
- 主要类：
  - `LLMConfig`：LLM 配置模型
  - `ProjectSettings`：项目总配置（继承 BaseSettings）
  - `get_settings()`：获取配置单例

#### 关键设计
\`\`\`python
from pydantic_settings import BaseSettings, SettingsConfigDict

class ProjectSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
    llm_api_key: str = Field(validation_alias=AliasChoices('llm_api_key', 'LLM_KEY'))

_settings_instance = None

def get_settings() -> ProjectSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ProjectSettings()
    return _settings_instance
\`\`\`

### 使用示例
\`\`\`python
from core.models import get_settings

settings = get_settings()
api_key = settings.llm_api_key
model = settings.llm_model
\`\`\`
```

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

# 5. 运行单元测试 (可选)
python -m pytest tests/unit/ -v
```

**验证成功标准**：
- ✅ 主流程完整执行无错误
- ✅ 生成需求分析、测试用例、评审结果
- ✅ 执行测试脚本 (即使失败也要有执行记录)
- ✅ 自动生成并打开 Allure 报告
- ✅ 所有输出文件正确生成

## 🚀 核心工作流

### 阶段 1：需求文档分析 (已集成 Pydantic)

当用户提供需求文档后：

1. **读取需求文档** - 支持 Markdown、PDF、Word 格式
2. **调用需求分析 Agent** - 使用 LLM 分析需求，集成 Pydantic 数据验证
3. **输出结构化需求** - 类型安全的 Pydantic 模型

**新的导入路径**:
```python
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.requirement import Requirement, RequirementAnalysisResult
```

**需求分析 Agent 使用方式**:
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

**Pydantic 需求模型**:
```python
class Requirement(BaseModel):
    id: str = Field(pattern=r"^REQ_\d{3}$")  # 自动验证ID格式
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10)
    priority: Priority = Field(default=Priority.MEDIUM)
    type: RequirementType = Field(default=RequirementType.FUNCTIONAL)
    acceptance_criteria: List[str] = Field(default_factory=list)
    ui_elements: List[str] = Field(default_factory=list)
```

**数据验证优势**:
- 自动验证 ID 格式 (REQ_001)
- 字段长度检查
- 业务规则验证
- 类型安全保证
- IDE 完整支持

### 阶段 2：测试用例生成 (已集成 Pydantic)

基于需求分析结果调用测试用例生成 Agent：

1. **为每个需求生成测试用例** - 包含正向和负向测试

**新的导入路径**:
```python
from core.agents.test_case_generator import TestCaseGenerator
from core.models.test_case import TestCase, TestCaseGenerationResult, TestStep, TestCaseType
```

**测试用例生成 Agent 使用方式**:
```python
generator = TestCaseGenerator()

# 向后兼容的字典接口
test_cases_dict = generator.generate(requirement)

# 新的类型安全接口 (推荐)
result = generator.generate_structured(requirement)  # requirement 是 Requirement 模型

# 使用便捷方法
high_priority = result.get_test_cases_by_priority(Priority.HIGH)
functional_tests = result.get_test_cases_by_type(TestCaseType.FUNCTIONAL)
```

**Pydantic 测试用例模型**:
```python
class TestCase(BaseModel):
    id: str = Field(pattern=r"^TC_\d{3}$")  # 自动验证ID格式
    requirement_id: str = Field(pattern=r"^REQ_\d{3}$")
    title: str = Field(min_length=5, max_length=200)
    priority: Priority = Field(default=Priority.MEDIUM)
    type: TestCaseType = Field(default=TestCaseType.FUNCTIONAL)
    steps: List[TestStep] = Field(min_length=1)  # 至少一个步骤
    expected: str = Field(min_length=5)
    tags: List[str] = Field(default_factory=list)
```

### 阶段 3：测试用例评审 (已集成 Pydantic)

执行自动评审检查：

1. **覆盖率检查** - 确保所有需求点都有对应用例
2. **重复性检查** - 识别重复或高度相似的用例
3. **可执行性检查** - 验证步骤描述是否可被自动化执行
4. **边界值检查** - 确认包含边界条件和异常场景
5. **优先级合理性** - 审查 P0 用例是否为核心场景

**新的导入路径**:
```python
from core.agents.case_reviewer import CaseReviewer
from core.models.review import (
    ReviewResult, ReviewAllResult, ReviewDimensions, ReviewComment,
    RequirementReviewDetail, CommentType, CommentSeverity
)
```

**评审 Agent 使用方式**:
```python
reviewer = CaseReviewer()

# 向后兼容的字典接口
result_dict = reviewer.review(requirement, test_cases)
all_result_dict = reviewer.review_all(requirements, test_cases)

# 新的类型安全接口 (推荐)
result = reviewer.review_structured(requirement, test_cases)
all_result = reviewer.review_all_structured(requirements, test_cases)

# 使用便捷方法
failed_details = all_result.get_failed_details()
passed_count = all_result.get_passed_count()
```

**Pydantic 评审模型**:
```python
class ReviewDimensions(BaseModel):
    completeness: int = Field(ge=0, le=20)   # 完整性
    coverage: int = Field(ge=0, le=20)       # 覆盖率
    reasonability: int = Field(ge=0, le=20)  # 合理性
    independence: int = Field(ge=0, le=20)   # 独立性
    clarity: int = Field(ge=0, le=20)        # 清晰度

class ReviewResult(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    dimensions: Optional[ReviewDimensions]
    comments: List[ReviewComment]
    suggestions: List[str]
```

**评审报告输出**:
- 用例总数统计
- 覆盖率分析 (需求->用例映射)
- 问题清单及修改建议
- 评审结论 (通过/需修改/不通过)

### 阶段 4：自动化脚本生成

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

### 阶段 5：测试执行与报告 (已优化)

**执行测试**:
```bash
# 在虚拟环境中执行
.venv\Scripts\activate

# 执行全部测试
pytest tests/generated/ --alluredir=allure-results

# 执行 P0 用例 (冒烟测试)
pytest tests/generated/ -m smoke --alluredir=allure-results

# 并行执行
pytest tests/generated/ -n auto --alluredir=allure-results

# 失败重试
pytest tests/generated/ --reruns 2 --alluredir=allure-results
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

# 快速预览
allure serve allure-results
```

**报告生成优化**：
- ✅ 自动降级处理：当测试失败时仍能生成报告
- ✅ 智能结果检测：自动检查并生成缺失的 Allure 数据
- ✅ 浏览器自动打开：无需手动访问报告地址
- ✅ 错误信息完整：包含详细的失败原因和堆栈信息

## 🔧 配置模板

### 虚拟环境配置

**创建和管理虚拟环境**：
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)  
source .venv/bin/activate

# 升级 pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证安装
pip list
python -c "import langchain; print('LangChain installed successfully')"
```

### config.yaml
```yaml
project:
  name: "AI 测试自动化平台"
  version: "0.1.0"

llm:
  model: ""  # 由环境变量 LLM_MODEL 配置
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

### playwright.config.ts (已优化)
```typescript
import { defineConfig, devices } from '@playwright/test';
import { config } from 'dotenv';
import path from 'path';

// 加载 .env 文件
config();

// 浏览器下载到项目目录，避免占用 C 盘空间
process.env.PLAYWRIGHT_BROWSERS_PATH = process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(__dirname, 'browsers');

export default defineConfig({
  testDir: './midscene_run/generated',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 60000,  // 每个测试最长 60 秒
  reporter: [
    ['list'],
    ['allure-playwright', { 
      outputFolder: './allure-results',
      suiteTitle: false,
      detail: true
    }]
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',  // 禁用视频录制，避免需要 ffmpeg
    actionTimeout: 10000,  // 每个操作最长 10 秒
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: undefined,
  globalSetup: undefined,
  expect: {
    timeout: 10000,
  },
});
```
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

### pytest.ini
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
# LLM API 密钥
LLM_KEY=your_api_key_here

# LLM 模型选择
LLM_MODEL=your_model_name
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

## LLM 集成

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

## 🔄 阶段复盘机制 (强制要求)

### 复盘原则

**核心要求**：每完成一个开发阶段或解决一个重要问题后，必须进行复盘并记录，避免重复犯错。

### 复盘时机

1. **阶段开始时** - 回顾上一阶段的复盘文档，了解已完成工作和遇到的问题
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

### 复盘文档模板

```markdown
# 阶段 X.X [阶段名称] - 复盘文档

**日期**: YYYY-MM-DD  
**阶段**: X.X [阶段名称]  
**状态**: ✅ 完成 / 🔄 进行中 / ❌ 阻塞  
**参与人员**: [开发人员]

---

## 一、目标与背景

### 1.1 阶段目标
[本阶段的主要目标和预期成果]

### 1.2 背景说明
[为什么要做这个阶段，解决什么问题]

---

## 二、完成的工作

### 2.1 创建/修改的文件

| 文件路径 | 用途 | 状态 |
|----------|------|------|
| core/agents/requirement_analyzer.py | 需求分析Agent | ✅ 完成 |
| core/models/requirement.py | Pydantic数据模型 | ✅ 完成 |

### 2.2 安装的依赖

```bash
pip install pydantic==2.10.3
```

### 2.3 配置的环境变量

```bash
# 新增环境变量
PYDANTIC_VALIDATE_ASSIGNMENT=true
```

### 2.4 验证结果

[测试结果、截图或验证命令]

```bash
python tests/unit/test_analyzer_core.py
# 测试结果: 3/3 通过 ✅
```

---

## 三、遇到的困难与解决方案

### 困难 1：Pydantic V2 兼容性问题

**问题描述**：
- 使用了 `regex` 参数，在 Pydantic V2 中已改为 `pattern`
- `@validator` 装饰器已弃用，需要使用 `@field_validator`
- `json()` 方法改为 `model_dump_json()`

**错误信息**：
```
PydanticUserError: `regex` is removed. use `pattern` instead
```

**解决方案**：
1. 将所有 `regex=` 改为 `pattern=`
2. 更新验证器语法：
   ```python
   # 旧语法
   @validator('field_name')
   def validate_field(cls, v):
       return v
   
   # 新语法
   @field_validator('field_name')
   @classmethod
   def validate_field(cls, v):
       return v
   ```
3. 更新序列化方法：
   ```python
   # 旧方法
   model.json()
   model.dict()
   
   # 新方法
   model.model_dump_json()
   model.model_dump()
   ```

**预防措施**：
- 查看 Pydantic 版本兼容性文档
- 使用最新的 API 语法
- 添加版本检查

### 困难 2：导入路径更新

**问题描述**：
项目重构后，所有导入路径需要更新为 `core.` 前缀

**解决方案**：
1. 创建批量更新脚本 `scripts/update_imports.py`
2. 系统性更新所有文件的导入路径
3. 验证更新后的功能正常

**经验教训**：
- 大规模重构前应该先做好备份
- 使用脚本自动化重复性工作
- 分步骤验证，避免一次性改动过多

---

## 四、关键经验总结

### 4.1 技术经验

**Pydantic 集成最佳实践**：
- 保持向后兼容性，提供新旧两套接口
- 使用降级处理机制，确保系统稳定性
- 充分利用 Pydantic 的验证功能，提前发现数据问题

**项目结构设计**：
- 模块化设计，核心功能集中在 `core/` 目录
- 测试文件按类型分类，便于管理
- 文档集中管理，便于查找和维护

### 4.2 开发流程

**渐进式改进策略**：
- 不要一次性改动过多，分阶段进行
- 每个阶段都要有完整的测试验证
- 保持向后兼容，降低风险

### 4.3 问题解决

**调试技巧**：
- 使用模拟数据进行单元测试，避免依赖外部服务
- 创建简化版本验证核心逻辑
- 详细记录错误信息和解决过程

---

## 五、下一步计划

| 阶段 | 任务 | 优先级 | 预计时间 | 状态 |
|------|------|--------|----------|------|
| 3.2 | 测试用例生成Agent Pydantic集成 | P1 | 2天 | 📋 待开始 |
| 3.3 | 评审Agent Pydantic集成 | P1 | 1天 | 📋 待开始 |
| 3.4 | 工作流状态管理优化 | P2 | 3天 | 📋 待开始 |

---

## 🎯 运行命令备忘 (虚拟环境)

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

# 测试需求分析Agent
python -c "
from core.agents.requirement_analyzer import RequirementAnalyzer
analyzer = RequirementAnalyzer()
print('需求分析Agent加载成功')
"

# 运行单元测试
python -m pytest tests/unit/ -v

# 生成 Allure 报告 (手动)
python scripts/generate_allure_from_results.py
allure generate allure-results -o allure-report --clean
```

### 故障排除
```bash
# 检查导入路径
python -c "from core.agents.requirement_analyzer import RequirementAnalyzer; print('导入成功')"

# 检查 LLM 配置
python -c "from core.utils.llm_client import get_llm_client; print('LLM 客户端可用')"

# 检查 Allure 安装
allure --version

# 重新安装依赖
pip install -r requirements.txt
```

---

## 七、参考资料

- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/2.0/migration/)
- [Python项目结构最佳实践](https://docs.python-guide.org/writing/structure/)
- [项目重构经验总结](docs/improvements/project_improvements/)

---

## 八、复盘检查清单

- [ ] 阶段目标和完成状态明确
- [ ] 创建/修改的文件列表完整
- [ ] 安装的依赖和配置记录
- [ ] 遇到的每个困难及解决方案详细
- [ ] 关键经验总结（供后续阶段参考）
- [ ] 下一步计划具体可执行
- [ ] 常用命令备忘录完整
- [ ] 参考资料链接有效
```

### 问题解决记录模板

对于日常遇到的问题，使用简化模板快速记录：

```markdown
## 问题：[简短描述]

**时间**: YYYY-MM-DD HH:MM  
**类型**: 🐛 Bug / ⚠️ 警告 / 💡 改进 / 📚 学习

**问题描述**：
[详细描述问题现象]

**解决方案**：
[具体的解决步骤]

**根本原因**：
[问题的根本原因分析]

**预防措施**：
[如何避免类似问题再次发生]

**相关文件**：
- [涉及的文件列表]

**验证命令**：
```bash
[验证解决方案的命令]
```
```

### 复盘文档索引维护

在 `docs/retrospectives/README.md` 中维护索引：

```markdown
# 阶段复盘索引

## 📋 阶段复盘

| 阶段 | 文档 | 状态 | 关键成果 | 主要问题 |
|------|------|------|----------|----------|
| 1.0 | [phase1-hello-world.md](./phase1-hello-world.md) | ✅ | 基础流程搭建 | LLM集成 |
| 2.0 | [phase2-agent-workflow.md](./phase2-agent-workflow.md) | ✅ | LangGraph工作流 | 状态管理 |
| 2.1 | [pydantic-integration.md](./pydantic-integration.md) | ✅ | Pydantic数据验证 | V2兼容性 |
| 2.2 | [project-restructure.md](./project-restructure.md) | ✅ | 项目结构重构 | 导入路径 |

## 🔧 问题解决记录

| 问题类型 | 文档 | 解决状态 |
|----------|------|----------|
| 常见问题 | [common-issues.md](./common-issues.md) | 🔄 持续更新 |
| 环境配置 | [environment-setup.md](./environment-setup.md) | ✅ |
| 依赖管理 | [dependency-issues.md](./dependency-issues.md) | ✅ |

## 📚 经验总结

- **技术选型**: 优先选择成熟稳定的技术栈
- **版本管理**: 及时关注依赖包的版本兼容性
- **测试策略**: 单元测试 + 集成测试 + 端到端测试
- **文档维护**: 及时更新文档，记录重要决策
```

---

## 学习路线

### 阶段 1：Hello World (已完成)
- [x] 基础项目结构
- [x] 需求分析 Agent
- [x] 测试用例生成 Agent
- [x] 脚本生成器
- [x] 端到端流程演示

### 阶段 2：Agent 化 (已完成)
- [x] 引入 LangGraph 状态机
- [x] 实现工作流编排
- [x] LLM 智能评审 Agent
- [x] 评审不通过自动迭代重试

### 阶段 3：智能化元素定位 (进行中)
- [x] 3.1 Midscene 环境搭建 + Demo
- [ ] 3.2 实现 MidsceneScriptGenerator
- [ ] 3.3 实现 TestExecutor
- [ ] 3.4 集成到 LangGraph 工作流
- [ ] 3.5 Allure 报告集成

### 阶段 4：工程化
- [ ] 数据库集成 (PostgreSQL)
- [ ] 版本管理
- [ ] API 接口

### 阶段 5：智能化
- [ ] 测试策略 Agent
- [ ] 失败分析 Agent
- [ ] 用例优化

### 阶段 6：前端界面
- [ ] React 前端
- [ ] 文档上传
- [ ] 报告展示

## ❓ 常见问题与解决方案

**Q: 生成的测试脚本无法运行？**
A: 阶段 1 生成的脚本是模板，需要手动调整选择器。阶段 2 会改进为更智能的生成。

**Q: API 调用失败？**
A: 检查 `.env` 文件中的 `LLM_KEY` 是否正确配置。

**Q: 如何调整生成的测试用例？**
A: 修改 `core/agents/test_case_generator.py` 中的 prompt 模板。

**Q: 如何查看 Allure 报告？**
A: 主流程会自动生成并打开报告。手动查看：`allure serve allure-results`。

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

## 复盘文档要求

**强制执行**：每次解决问题后必须创建或更新复盘文档，记录在 `docs/retrospectives/` 目录。

### 复盘文档类型

1. **阶段复盘** - 完成一个开发阶段后的完整总结
2. **问题解决记录** - 遇到具体问题的解决过程
3. **经验总结** - 技术选型和最佳实践

### 复盘检查清单

- [ ] 问题描述清晰具体
- [ ] 解决方案步骤详细
- [ ] 根本原因分析到位
- [ ] 预防措施可执行
- [ ] 相关文件和命令完整
- [ ] 经验教训总结

### 复盘文档索引

维护 `docs/retrospectives/README.md` 作为所有复盘文档的索引，便于查找和学习。
