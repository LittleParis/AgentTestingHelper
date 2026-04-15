# 阶段3：智能化元素定位 - 技术设计文档

## 1. 背景与问题

### 1.1 当前状态
- ✅ 阶段2已完成：LangGraph工作流 + LLM智能评审
- 测试用例步骤使用自然语言描述（如"输入用户名"、"点击登录按钮"）
- `script_generator.py` 使用简单关键词匹配生成 Playwright 脚本

### 1.2 核心问题
```python
# 当前生成的代码（无法直接运行）
await page.fill("input", "admin")      # 选择器太泛，无法定位具体输入框
await page.click("button")             # 选择器太泛，无法定位具体按钮
```

**问题**：
1. 选择器不精确 - 使用通用标签名，无法定位具体元素
2. 无法自动识别页面结构 - 需要人工分析 DOM
3. 生成的脚本无法直接执行

## 2. 解决方案：集成 Midscene

### 2.1 Midscene 简介
Midscene.js 是 AI 驱动的 UI 自动化工具，核心能力：
- **自然语言定位** - 用描述性语言定位元素，无需精确选择器
- **AI 理解页面** - 自动分析页面结构
- **智能断言** - 用自然语言描述预期结果

```javascript
// Midscene 示例
await ai('在用户名输入框中输入 "admin"');
await ai('点击登录按钮');
await ai('验证页面显示 "欢迎回来"');
```

### 2.2 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    阶段3 架构图                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ 测试用例      │    │ Midscene     │    │ Playwright   │  │
│  │ (自然语言)    │───▶│ Agent        │───▶│ 测试脚本     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                    │          │
│         ▼                   ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ test_cases   │    │ AI元素定位   │    │ 可执行脚本   │  │
│  │ .json        │    │ 智能断言     │    │ .spec.ts     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 3. 模块设计

### 3.1 新增模块

```
automation/
├── script_generator.py      # 现有：基础脚本生成（保留）
├── midscene_generator.py    # 新增：Midscene脚本生成器
├── element_locator.py       # 新增：AI元素定位器
└── test_executor.py         # 新增：测试执行器
```

### 3.2 Midscene 脚本生成器

```python
# automation/midscene_generator.py

class MidsceneScriptGenerator:
    """生成 Midscene + Playwright 测试脚本"""

    def generate(self, test_case: Dict, page_url: str) -> str:
        """
        将测试用例转换为 Midscene 脚本

        Args:
            test_case: 测试用例（含自然语言步骤）
            page_url: 目标页面URL

        Returns:
            可执行的 TypeScript 测试脚本
        """
        pass

    def _convert_step_to_midscene(self, step: Dict) -> str:
        """
        将测试步骤转换为 Midscene AI 指令

        输入: {"action": "输入用户名", "data": "admin"}
        输出: await ai('在用户名输入框中输入 "admin"')
        """
        pass
```

### 3.3 AI 元素定位器

```python
# automation/element_locator.py

class AIElementLocator:
    """AI驱动的元素定位器"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def analyze_page(self, page_html: str) -> Dict:
        """
        分析页面结构，提取关键元素信息

        Returns:
            {
                "elements": [
                    {"type": "input", "purpose": "用户名输入", "selector": "#username"},
                    {"type": "button", "purpose": "登录按钮", "selector": ".login-btn"}
                ]
            }
        """
        pass

    def suggest_selector(self, element_description: str, page_context: str) -> str:
        """
        根据元素描述推荐选择器

        Args:
            element_description: "用户名输入框"
            page_context: 页面HTML片段

        Returns:
            推荐的 CSS 选择器
        """
        pass
```

### 3.4 测试执行器

```python
# automation/test_executor.py

class TestExecutor:
    """测试执行器"""

    def __init__(self):
        self.results = []

    def run_test(self, script_path: str) -> Dict:
        """
        执行测试脚本并收集结果

        Returns:
            {
                "status": "passed" | "failed",
                "duration": 1.5,
                "steps": [...],
                "screenshot": "path/to/screenshot.png"
            }
        """
        pass

    def generate_allure_report(self, results_dir: str) -> str:
        """生成 Allure 报告"""
        pass
```

## 4. 工作流设计

### 4.1 阶段3 完整流程

```
需求文档
    │
    ▼
┌─────────────────┐
│ 需求分析 Agent  │  (已有)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 测试用例生成    │  (已有)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 用例评审 Agent  │  (已有)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Midscene 脚本生成 (新增)             │
│  - 解析自然语言步骤                  │
│  - 生成 AI 定位指令                  │
│  - 生成 Playwright + Midscene 脚本   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 测试执行 (新增)                      │
│  - 启动浏览器                        │
│  - 执行 Midscene 指令                │
│  - 收集执行结果                      │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 报告生成 (新增)                      │
│  - Allure 报告                       │
│  - 截图附件                          │
│  - 执行日志                          │
└─────────────────────────────────────┘
```

### 4.2 LangGraph 状态扩展

```python
# agents/workflow.py 状态扩展

class AgentState(TypedDict):
    # 现有字段
    requirement: Dict
    test_cases: List[Dict]
    review_result: Dict

    # 新增字段
    generated_scripts: List[str]      # 生成的脚本路径
    execution_results: List[Dict]     # 执行结果
    report_path: str                  # 报告路径
```

## 5. 技术选型

### 5.1 Midscene.js

| 项目 | 说明 |
|------|------|
| 官网 | https://midscenejs.com |
| GitHub | https://github.com/web-infra-dev/midscene |
| 安装 | `npm install @midscene/web` |
| 特点 | AI驱动、自然语言定位、与Playwright无缝集成 |

### 5.2 依赖安装

```bash
# Node.js 依赖
npm install @midscene/web playwright @playwright/test

# Python 依赖（用于调用）
pip install playwright-pytest
```

### 5.3 配置文件

```yaml
# config.yaml 新增配置
midscene:
  enabled: true
  ai_model: "gpt-4o"  # Midscene 使用的 AI 模型
  timeout: 30000      # AI 定位超时时间

execution:
  browser: "chromium"
  headless: false
  screenshot_on_failure: true
  video: true
```

## 6. 实现计划

### 6.1 里程碑

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| 3.1 | Midscene 环境搭建 + Demo | 1天 |
| 3.2 | 实现 `MidsceneScriptGenerator` | 2天 |
| 3.3 | 实现 `TestExecutor` | 1天 |
| 3.4 | 集成到 LangGraph 工作流 | 1天 |
| 3.5 | Allure 报告集成 | 1天 |
| 3.6 | 测试与优化 | 2天 |

### 6.2 详细任务

#### 3.1 Midscene 环境搭建
- [ ] 安装 Node.js 依赖
- [ ] 配置 Midscene AI 模型（需要 OpenAI API Key）
- [ ] 编写第一个 Demo 脚本
- [ ] 验证 AI 定位能力

#### 3.2 MidsceneScriptGenerator
- [ ] 设计测试用例到 Midscene 指令的映射规则
- [ ] 实现步骤转换逻辑
- [ ] 生成 TypeScript 测试脚本
- [ ] 处理断言和验证

#### 3.3 TestExecutor
- [ ] 封装 Playwright 执行环境
- [ ] 实现测试脚本执行
- [ ] 收集执行结果和截图
- [ ] 错误处理和重试机制

#### 3.4 工作流集成
- [ ] 扩展 AgentState
- [ ] 添加脚本生成节点
- [ ] 添加测试执行节点
- [ ] 端到端测试

#### 3.5 报告集成
- [ ] Allure 报告生成
- [ ] 截图和视频附件
- [ ] 执行日志记录

## 7. 示例代码

### 7.1 Midscene 测试脚本示例

```typescript
// tests/generated/login.spec.ts
import { test, expect } from '@playwright/test';
import { Midscene } from '@midscene/web';

test.describe('登录功能测试', () => {
  test('TC_001: 正确的用户名和密码登录', async ({ page }) => {
    // 创建 Midscene 实例
    const midscene = new Midscene(page);

    // 访问登录页面
    await page.goto('https://example.com/login');

    // AI 驱动的操作
    await midscene.ai('在用户名输入框中输入 "admin"');
    await midscene.ai('在密码输入框中输入 "password123"');
    await midscene.ai('点击登录按钮');

    // AI 驱动的断言
    await midscene.ai('验证页面显示 "欢迎回来" 或跳转到首页');
  });
});
```

### 7.2 Python 调用示例

```python
# main_v3.py (阶段3入口)

async def run_phase3():
    """阶段3：智能化元素定位"""

    # 1. 阶段2的流程（需求分析 → 用例生成 → 评审）
    workflow = TestWorkflow()
    result = await workflow.run("examples/requirement_login.md")

    # 2. 生成 Midscene 脚本
    generator = MidsceneScriptGenerator()
    scripts = []
    for test_case in result["test_cases"]:
        script = generator.generate(
            test_case=test_case,
            page_url="https://example.com/login"
        )
        script_path = f"tests/generated/{test_case['id']}.spec.ts"
        generator.save(script, script_path)
        scripts.append(script_path)

    # 3. 执行测试
    executor = TestExecutor()
    for script_path in scripts:
        execution_result = await executor.run_test(script_path)
        result["execution_results"].append(execution_result)

    # 4. 生成报告
    report_path = executor.generate_allure_report("allure-results")

    return result
```

## 8. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| Midscene AI 定位不稳定 | 测试执行失败 | 增加重试机制，提供手动选择器回退 |
| OpenAI API 调用成本 | 成本增加 | 缓存定位结果，支持本地模型 |
| 页面结构变化 | 脚本失效 | Midscene AI 有一定容错能力 |
| 执行环境依赖 Node.js | 环境复杂度 | 使用 Playwright Python 版 + Midscene |

## 9. 验收标准

### 9.1 功能验收
- [ ] 能够从测试用例生成可执行的 Midscene 脚本
- [ ] 脚本能够自动定位页面元素（无需手动指定选择器）
- [ ] 测试执行成功率 > 80%
- [ ] 能够生成 Allure 测试报告

### 9.2 质量验收
- [ ] 代码覆盖率 > 70%
- [ ] 有完整的单元测试
- [ ] 文档完整（README + API 文档）

## 10. 参考资料

- [Midscene.js 官方文档](https://midscenejs.com)
- [Playwright 文档](https://playwright.dev/python/)
- [Allure 报告](https://docs.qameta.io/allure/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
