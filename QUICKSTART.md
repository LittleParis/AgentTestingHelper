# 快速启动指南

## 第一次运行（5分钟）

### 1. 安装Python依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt
```

### 2. 安装Playwright浏览器

```bash
playwright install chromium
```

### 3. 配置API密钥

```bash
# 复制环境变量模板
copy .env.example .env

# 用记事本或VS Code编辑.env文件
notepad .env
```

在 `.env` 文件中填入你的Claude API密钥：
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 4. 运行演示

```bash
python main.py
```

你会看到：
```
============================================================
AI测试自动化平台 - 阶段1演示
============================================================

[步骤1] 读取需求文档...
✓ 需求文档读取成功 (xxx 字符)

[步骤2] 分析需求...
✓ 需求分析完成，识别到 1 个需求
  已保存到: output/requirements.json

[步骤3] 生成测试用例...
  ✓ REQ_001: 生成 3 个测试用例
✓ 总共生成 3 个测试用例
  已保存到: output/test_cases.json

[步骤4] 生成测试脚本...
  ✓ TC_001: tests/generated/tc_001.py
  ✓ TC_002: tests/generated/tc_002.py
  ✓ TC_003: tests/generated/tc_003.py
✓ 测试脚本生成完成

============================================================
✓ 阶段1流程完成！
============================================================
```

### 5. 查看生成的内容

```bash
# 查看需求分析结果
type output\requirements.json

# 查看测试用例
type output\test_cases.json

# 查看生成的测试脚本
dir tests\generated\
```

## 理解生成的内容

### 需求分析结果 (output/requirements.json)
```json
{
  "requirements": [
    {
      "id": "REQ_001",
      "title": "用户登录功能",
      "description": "...",
      "priority": "high",
      "acceptance_criteria": [...]
    }
  ]
}
```

### 测试用例 (output/test_cases.json)
```json
{
  "test_cases": [
    {
      "id": "TC_001",
      "title": "正常登录流程",
      "steps": [
        {"action": "打开登录页面", "data": "..."},
        {"action": "输入邮箱", "data": "test@example.com"}
      ],
      "expected": "成功跳转到首页"
    }
  ]
}
```

### 测试脚本 (tests/generated/tc_001.py)
```python
@allure.title("正常登录流程")
async def test_tc_001(page: Page):
    with allure.step("步骤1: 打开登录页面"):
        await page.goto("https://example.com/login")
    # ...
```

## 下一步

### 尝试修改需求文档

编辑 `examples/requirement_login.md`，添加新的需求：

```markdown
# 用户注册功能需求

## 功能描述
新用户应该能够注册账号...
```

然后重新运行 `python main.py`

### 运行生成的测试（需要调整）

生成的测试脚本是模板，需要手动调整选择器：

```bash
# 运行测试
pytest tests/generated/tc_001.py -v

# 生成Allure报告
pytest tests/generated/ --alluredir=allure-results
allure serve allure-results
```

## 常见问题

### Q: 提示 "ANTHROPIC_API_KEY not found"
A: 检查 `.env` 文件是否存在且包含正确的API密钥

### Q: 提示 "No module named 'anthropic'"
A: 运行 `pip install -r requirements.txt`

### Q: 生成的测试脚本无法运行
A: 阶段1的脚本是模板，需要手动调整。阶段2会改进。

### Q: 想要生成更多测试用例
A: 修改 `agents/test_case_generator.py` 中的prompt，要求生成更多用例

## 学习建议

1. **先运行一遍**：理解整个流程
2. **查看生成的JSON**：理解数据结构
3. **修改需求文档**：看Agent如何适应
4. **调整Prompt**：优化生成质量
5. **准备进入阶段2**：引入LangGraph

## 进入阶段2

当你熟悉了阶段1的流程后，告诉我：
"我准备好进入阶段2了"

我会帮你：
- 引入LangGraph状态机
- 实现工作流编排
- 添加Tool Calling
- 优化整体架构
