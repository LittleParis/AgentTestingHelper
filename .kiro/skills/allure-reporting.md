---
name: allure-reporting
description: Allure测试报告集成技能
tags: [testing, reporting, allure]
---

# Allure报告集成技能

## 基础配置

### 安装和初始化
```bash
# 安装Allure
pip install allure-pytest

# 生成报告
pytest --alluredir=./allure-results
allure serve ./allure-results
```

### pytest配置
```ini
# pytest.ini
[pytest]
addopts = 
    --alluredir=allure-results
    --clean-alluredir
    -v
```

## 装饰器使用

### 基础标注
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

@allure.step("输入用户凭证: {email}")
async def enter_credentials(page, email: str, password: str):
    await page.ai_action("在邮箱输入框输入", text=email)
    await page.ai_action("在密码输入框输入", text=password)

@allure.step("点击登录按钮")
async def click_login(page):
    await page.ai_action("点击登录按钮")

# 使用
async def test_login():
    page = await setup_page()
    await open_login_page(page)
    await enter_credentials(page, "test@example.com", "password")
    await click_login(page)
```

## 附件管理

### 截图附件
```python
@allure.step("验证登录成功")
async def verify_login_success(page):
    screenshot = await page.screenshot()
    allure.attach(
        screenshot,
        name="登录成功页面",
        attachment_type=allure.attachment_type.PNG
    )
    
    assert await page.ai_query("是否显示用户头像")
```

### 日志附件
```python
def attach_logs(log_content: str):
    allure.attach(
        log_content,
        name="执行日志",
        attachment_type=allure.attachment_type.TEXT
    )

# 自动附加失败日志
@pytest.fixture(autouse=True)
def attach_logs_on_failure(request):
    yield
    if request.node.rep_call.failed:
        with open("test.log") as f:
            attach_logs(f.read())
```

### JSON数据附件
```python
import json

def attach_test_data(data: dict):
    allure.attach(
        json.dumps(data, indent=2, ensure_ascii=False),
        name="测试数据",
        attachment_type=allure.attachment_type.JSON
    )

# 使用
test_case = {"id": "TC001", "title": "登录测试"}
attach_test_data(test_case)
```

## 动态报告增强

### 环境信息
```python
# conftest.py
import pytest

@pytest.fixture(scope="session", autouse=True)
def environment_info(request):
    """添加环境信息到报告"""
    import platform
    
    env_properties = {
        "操作系统": platform.system(),
        "Python版本": platform.python_version(),
        "测试环境": "Staging",
        "浏览器": "Chrome 120",
        "执行人": "Agent",
    }
    
    allure_env_path = "allure-results/environment.properties"
    with open(allure_env_path, "w", encoding="utf-8") as f:
        for key, value in env_properties.items():
            f.write(f"{key}={value}\n")
```

### 分类统计
```python
# 按需求分类
@allure.epic("电商平台")
@allure.feature("订单管理")
@allure.story("创建订单")
def test_create_order():
    pass

# 按测试类型分类
@allure.suite("功能测试")
@allure.sub_suite("支付模块")
def test_payment():
    pass
```

## Agent集成

### 自动生成Allure装饰器
```python
def generate_allure_decorators(test_case: dict) -> str:
    """根据测试用例JSON生成Allure装饰器"""
    decorators = []
    
    # Feature和Story
    if "feature" in test_case:
        decorators.append(f'@allure.feature("{test_case["feature"]}")')
    if "story" in test_case:
        decorators.append(f'@allure.story("{test_case["story"]}")')
    
    # 标题和描述
    decorators.append(f'@allure.title("{test_case["title"]}")')
    if "description" in test_case:
        decorators.append(f'@allure.description("{test_case["description"]}")')
    
    # 优先级映射
    severity_map = {
        "critical": "allure.severity_level.CRITICAL",
        "high": "allure.severity_level.CRITICAL",
        "medium": "allure.severity_level.NORMAL",
        "low": "allure.severity_level.MINOR"
    }
    severity = severity_map.get(test_case.get("priority", "medium"))
    decorators.append(f'@allure.severity({severity})')
    
    # 标签
    if "tags" in test_case:
        tags = '", "'.join(test_case["tags"])
        decorators.append(f'@allure.tag("{tags}")')
    
    # 需求链接
    if "requirement_id" in test_case:
        decorators.append(
            f'@allure.link("https://jira.com/{test_case["requirement_id"]}", '
            f'name="{test_case["requirement_id"]}")'
        )
    
    return "\n".join(decorators)
```

### 完整测试生成
```python
def generate_allure_test(test_case: dict) -> str:
    """生成带Allure装饰器的完整测试"""
    decorators = generate_allure_decorators(test_case)
    
    script = f'''
import allure
from midscene import Page, expect

{decorators}
async def test_{test_case["id"].lower()}():
    """
    测试用例ID: {test_case["id"]}
    需求ID: {test_case.get("requirement_id", "N/A")}
    """
    page = await setup_page()
    
    try:
'''
    
    # 生成步骤
    for i, step in enumerate(test_case["steps"], 1):
        action = step["action"]
        data = step.get("data", "")
        
        script += f'''
        with allure.step("步骤{i}: {action}"):
'''
        if "输入" in action:
            script += f'            await page.ai_action("{action}", text="{data}")\n'
        else:
            script += f'            await page.ai_action("{action}")\n'
        
        # 添加截图
        script += f'            allure.attach(await page.screenshot(), name="步骤{i}", attachment_type=allure.attachment_type.PNG)\n'
    
    # 最终验证
    script += f'''
        with allure.step("验证: {test_case['expected']}"):
            await expect(page).to_contain_text("{test_case['expected']}")
            allure.attach(await page.screenshot(), name="最终结果", attachment_type=allure.attachment_type.PNG)
            
    except Exception as e:
        allure.attach(str(e), name="错误信息", attachment_type=allure.attachment_type.TEXT)
        allure.attach(await page.screenshot(), name="失败截图", attachment_type=allure.attachment_type.PNG)
        raise
    finally:
        await page.close()
'''
    
    return script
```

## 自定义报告

### 添加自定义分类
```python
# categories.json
[
  {
    "name": "Agent生成的测试",
    "matchedStatuses": ["passed", "failed"],
    "messageRegex": ".*test_tc.*"
  },
  {
    "name": "UI自动化失败",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*Midscene.*"
  },
  {
    "name": "断言失败",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*AssertionError.*"
  }
]
```

### 趋势分析
```python
# 保留历史报告
import shutil
from datetime import datetime

def archive_allure_results():
    """归档Allure结果用于趋势分析"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = f"allure-history/{timestamp}"
    
    shutil.copytree("allure-results", archive_dir)
    
    # 生成带历史的报告
    # allure generate allure-results -o allure-report --clean
```

## 报告优化

### 并行执行支持
```python
# pytest-xdist配置
# pytest.ini
[pytest]
addopts = 
    -n auto
    --dist loadfile
    --alluredir=allure-results
```

### 失败重试记录
```python
@pytest.mark.flaky(reruns=2)
@allure.title("不稳定的测试")
def test_flaky():
    with allure.step("尝试执行"):
        # 测试逻辑
        pass
```
