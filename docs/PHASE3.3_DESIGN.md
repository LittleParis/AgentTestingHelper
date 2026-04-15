# 阶段3.3 TestExecutor 实现 - 设计文档

**日期**: 2026-04-11
**阶段**: 3.3 TestExecutor 实现
**状态**: 📋 设计中

---

## 一、目标

实现 `TestExecutor` 模块，负责执行 Midscene 生成的测试脚本并收集执行结果。

---

## 二、功能需求

### 2.1 核心功能

| 功能 | 说明 |
|------|------|
| 执行测试脚本 | 调用 Playwright 执行 `.spec.ts` 测试脚本 |
| 收集执行结果 | 解析测试输出，提取通过/失败/跳过信息 |
| 截图管理 | 测试失败时自动截图，成功时可选截图 |
| 日志收集 | 收集 Playwright 执行日志和 Midscene AI 日志 |
| 结果统计 | 统计通过率、执行时间等指标 |

### 2.2 输入输出

```
输入: tests/generated/*.spec.ts (Midscene 测试脚本)
输出: {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "skipped": 0,
    "duration": 45.2,
    "results": [
        {
            "test_id": "TC_001",
            "title": "用户正常登录",
            "status": "passed",
            "duration": 3.5,
            "screenshot": null
        },
        {
            "test_id": "TC_002",
            "title": "密码错误登录",
            "status": "failed",
            "duration": 5.2,
            "error": "Timeout exceeded...",
            "screenshot": "screenshots/TC_002_failed.png"
        }
    ]
}
```

---

## 三、模块设计

### 3.1 类设计

```python
# automation/test_executor.py

class TestExecutor:
    """测试执行器 - 执行 Midscene 测试脚本"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化执行器

        Args:
            config: 配置选项
                - browser: 浏览器类型 (chromium/firefox/webkit)
                - headless: 是否无头模式
                - timeout: 超时时间(毫秒)
                - retries: 失败重试次数
                - screenshot_on_failure: 失败时截图
        """
        pass

    def run_tests(self, script_path: str) -> Dict:
        """
        执行测试脚本

        Args:
            script_path: 测试脚本路径或目录

        Returns:
            执行结果字典
        """
        pass

    def run_single_test(self, script_path: str, test_name: str) -> Dict:
        """
        执行单个测试用例

        Args:
            script_path: 测试脚本路径
            test_name: 测试用例名称

        Returns:
            单个测试的执行结果
        """
        pass

    def parse_playwright_output(self, output: str) -> Dict:
        """
        解析 Playwright 执行输出

        Args:
            output: Playwright CLI 输出

        Returns:
            解析后的结果字典
        """
        pass

    def get_execution_summary(self) -> Dict:
        """
        获取执行摘要

        Returns:
            {
                "total": 10,
                "passed": 8,
                "failed": 2,
                "duration": 45.2
            }
        """
        pass
```

### 3.2 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                    TestExecutor 执行流程                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                           │
│  │ 输入参数      │                                           │
│  │ script_path  │                                           │
│  └──────┬───────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                           │
│  │ 验证脚本存在  │                                           │
│  └──────┬───────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────┐                   │
│  │ 构建 Playwright 命令                  │                   │
│  │ npx playwright test {script_path}     │                   │
│  │   --reporter=list                     │                   │
│  │   --output=test-results               │                   │
│  └──────┬───────────────────────────────┘                   │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────┐                   │
│  │ 执行命令 (subprocess)                 │                   │
│  │ 捕获 stdout/stderr                    │                   │
│  └──────┬───────────────────────────────┘                   │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────┐                   │
│  │ 解析输出                              │                   │
│  │ - 提取测试结果                        │                   │
│  │ - 提取错误信息                        │                   │
│  │ - 提取执行时间                        │                   │
│  └──────┬───────────────────────────────┘                   │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────┐                   │
│  │ 收集附件                              │                   │
│  │ - 截图文件                            │                   │
│  │ - trace 文件                          │                   │
│  └──────┬───────────────────────────────┘                   │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                           │
│  │ 返回结果      │                                           │
│  │ Dict         │                                           │
│  └──────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Playwright 命令构建

```python
def _build_playwright_command(self, script_path: str) -> List[str]:
    """构建 Playwright 执行命令"""
    cmd = [
        "npx", "playwright", "test",
        script_path,
        "--reporter=list",
        f"--timeout={self.config.get('timeout', 60000)}",
        f"--retries={self.config.get('retries', 0)}",
    ]

    # 浏览器配置
    if self.config.get('headed'):
        cmd.append("--headed")

    # 项目配置
    if self.config.get('project'):
        cmd.extend(["--project", self.config['project']])

    return cmd
```

### 3.4 输出解析

Playwright 输出示例：
```
Running 3 tests using 1 worker

  ✓  [chromium] › login.spec.ts:10:3 › TC_001: 用户正常登录 (3.5s)
  ✓  [chromium] › login.spec.ts:25:3 › TC_002: 密码错误登录 (2.1s)
  ✘  [chromium] › login.spec.ts:40:3 › TC_003: 账号不存在 (5.2s)


  1 failed
  2 passed (10.8s)
```

解析逻辑：
```python
def parse_playwright_output(self, output: str) -> Dict:
    """解析 Playwright 输出"""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "duration": 0,
        "tests": []
    }

    # 正则匹配测试结果
    # ✓ 表示通过
    # ✘ 表示失败
    # - 表示跳过

    passed_pattern = r"✓.*›\s*(.+?)\s*\((\d+\.?\d*)s\)"
    failed_pattern = r"✘.*›\s*(.+?)\s*\((\d+\.?\d*)s\)"

    # ... 解析逻辑

    return results
```

---

## 四、配置设计

### 4.1 配置项

```python
DEFAULT_CONFIG = {
    # 浏览器配置
    "browser": "chromium",
    "headed": False,  # 无头模式
    "timeout": 60000,  # 60秒超时

    # 执行配置
    "retries": 0,  # 失败重试次数
    "workers": 1,  # 并行worker数

    # 截图配置
    "screenshot_on_failure": True,
    "screenshot_on_success": False,

    # 报告配置
    "reporter": "list",  # list/html/json
    "output_dir": "test-results",

    # 浏览器路径
    "browsers_path": "browsers",
}
```

### 4.2 环境变量

```bash
# 浏览器路径
PLAYWRIGHT_BROWSERS_PATH=G:/桌面/AgentTest/browsers

# Midscene AI 配置
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=xxx
MIDSCENE_MODEL_NAME=xxx
```

---

## 五、错误处理

### 5.1 错误类型

| 错误类型 | 说明 | 处理方式 |
|----------|------|----------|
| ScriptNotFound | 脚本文件不存在 | 返回错误，不执行 |
| PlaywrightError | Playwright 执行错误 | 捕获输出，返回错误信息 |
| TimeoutError | 测试超时 | 标记为失败，记录超时信息 |
| BrowserError | 浏览器启动失败 | 返回错误，检查浏览器安装 |

### 5.2 错误处理示例

```python
def run_tests(self, script_path: str) -> Dict:
    """执行测试脚本"""
    try:
        # 验证脚本存在
        if not os.path.exists(script_path):
            return {
                "status": "error",
                "error": f"Script not found: {script_path}"
            }

        # 执行测试
        result = subprocess.run(
            self._build_playwright_command(script_path),
            capture_output=True,
            text=True,
            timeout=self.config.get('timeout', 60000) / 1000 + 60
        )

        # 解析结果
        return self.parse_playwright_output(result.stdout)

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Test execution timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

---

## 六、与现有模块集成

### 6.1 与 MidsceneScriptGenerator 集成

```python
# 完整流程示例
from automation.midscene_generator import MidsceneScriptGenerator
from automation.test_executor import TestExecutor

# 1. 生成测试脚本
generator = MidsceneScriptGenerator()
script_path = generator.generate(test_cases, page_url="https://example.com/login")

# 2. 执行测试
executor = TestExecutor(config={"headed": True})
results = executor.run_tests(script_path)

# 3. 输出结果
print(f"通过: {results['passed']}/{results['total']}")
print(f"失败: {results['failed']}")
```

### 6.2 与 LangGraph 工作流集成 (阶段3.4)

```python
# agents/workflow.py 扩展

def execute_tests_node(state: AgentState) -> AgentState:
    """测试执行节点"""
    script_path = state.get("generated_script")

    executor = TestExecutor()
    results = executor.run_tests(script_path)

    return {
        **state,
        "execution_results": results
    }
```

---

## 七、测试计划

### 7.1 单元测试

```python
# tests/test_executor.py

def test_executor_init():
    """测试初始化"""
    executor = TestExecutor()
    assert executor.config is not None

def test_build_command():
    """测试命令构建"""
    executor = TestExecutor(config={"headed": True})
    cmd = executor._build_playwright_command("test.spec.ts")
    assert "--headed" in cmd

def test_parse_output():
    """测试输出解析"""
    executor = TestExecutor()
    output = """
    ✓  [chromium] › test.spec.ts:10:3 › TC_001: 测试 (3.5s)
    1 passed (3.5s)
    """
    result = executor.parse_playwright_output(output)
    assert result["passed"] == 1
```

### 7.2 集成测试

```python
def test_full_execution():
    """测试完整执行流程"""
    # 1. 生成脚本
    generator = MidsceneScriptGenerator()
    script_path = generator.generate(sample_test_cases)

    # 2. 执行测试
    executor = TestExecutor(config={"headed": True})
    results = executor.run_tests(script_path)

    # 3. 验证结果
    assert "total" in results
    assert results["total"] > 0
```

---

## 八、实现步骤

| 步骤 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 创建 `automation/test_executor.py` 基础结构 | 30分钟 |
| 2 | 实现 `run_tests()` 方法 | 1小时 |
| 3 | 实现 `parse_playwright_output()` 解析逻辑 | 1小时 |
| 4 | 添加错误处理和重试机制 | 30分钟 |
| 5 | 编写单元测试 | 1小时 |
| 6 | 集成测试验证 | 30分钟 |

---

## 九、验收标准

- [ ] 能够执行 `.spec.ts` 测试脚本
- [ ] 能够正确解析 Playwright 输出
- [ ] 能够收集测试结果（通过/失败/错误）
- [ ] 失败时能够获取截图路径
- [ ] 有完整的单元测试覆盖

---

## 十、参考资料

- [Playwright CLI 文档](https://playwright.dev/docs/test-cli)
- [Playwright Test 配置](https://playwright.dev/docs/test-configuration)
- [阶段3设计文档](./PHASE3_DESIGN.md)
- [阶段3.2复盘](./retrospectives/phase3.2-script-generator.md)
