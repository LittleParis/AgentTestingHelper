---
name: midscene-automation
description: Midscene UI自动化测试技能
tags: [ui-automation, midscene, playwright]
---

# Midscene UI自动化技能

## Midscene基础

### 初始化和配置
```python
from midscene import Page, expect, Config

# 配置
config = Config(
    headless=False,  # 开发时使用False便于调试
    viewport={"width": 1920, "height": 1080},
    timeout=30000,  # 默认超时30秒
    screenshot_on_failure=True,
    ai_model="claude-3-5-sonnet"  # AI视觉模型
)

async def setup_page():
    page = Page(config)
    await page.goto("https://example.com")
    return page
```

### AI视觉定位
```python
async def test_ai_actions():
    page = await setup_page()
    
    # 基础操作 - 使用自然语言描述
    await page.ai_action("点击蓝色的登录按钮")
    await page.ai_action("在用户名输入框输入", text="test@example.com")
    await page.ai_action("在密码框输入", text="password123")
    
    # 复杂操作 - 更具体的描述
    await page.ai_action("点击页面右上角的用户头像")
    await page.ai_action("在下拉菜单中选择'设置'选项")
    
    # 条件操作
    if await page.ai_query("页面上是否显示'欢迎回来'"):
        await page.ai_action("点击继续按钮")
```

### 智能等待
```python
async def smart_waiting():
    # 等待元素出现
    await page.ai_wait_for("登录成功提示消息", timeout=5000)
    
    # 等待元素消失
    await page.ai_wait_for_hidden("加载中的转圈图标")
    
    # 等待页面稳定（无网络请求）
    await page.wait_for_load_state("networkidle")
    
    # 等待特定条件
    await page.wait_for_function(
        "() => document.querySelectorAll('.item').length > 10"
    )
```

## 页面对象模式

### 定义页面对象
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class LoginPage:
    page: Page
    url: str = "https://example.com/login"
    
    async def navigate(self):
        """导航到登录页"""
        await self.page.goto(self.url)
        await self.page.ai_wait_for("登录表单")
    
    async def login(self, email: str, password: str):
        """执行登录操作"""
        await self.page.ai_action("在邮箱输入框输入", text=email)
        await self.page.ai_action("在密码输入框输入", text=password)
        await self.page.ai_action("点击登录按钮")
        await self.page.ai_wait_for("登录成功提示或首页")
    
    async def get_error_message(self) -> Optional[str]:
        """获取错误消息"""
        if await self.page.ai_query("是否显示错误消息"):
            return await self.page.ai_extract("错误消息的文本内容")
        return None
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return await self.page.ai_query("页面是否显示用户头像或用户名")

# 使用
async def test_login():
    page = await setup_page()
    login_page = LoginPage(page)
    
    await login_page.navigate()
    await login_page.login("test@example.com", "password123")
    
    assert await login_page.is_logged_in(), "登录失败"
```

### 组件封装
```python
class FormComponent:
    """表单组件封装"""
    
    def __init__(self, page: Page, form_description: str):
        self.page = page
        self.form_description = form_description
    
    async def fill_field(self, field_label: str, value: str):
        """填写表单字段"""
        await self.page.ai_action(
            f"在{self.form_description}中的{field_label}输入框输入",
            text=value
        )
    
    async def select_option(self, field_label: str, option: str):
        """选择下拉选项"""
        await self.page.ai_action(
            f"在{self.form_description}中的{field_label}下拉框选择{option}"
        )
    
    async def submit(self):
        """提交表单"""
        await self.page.ai_action(f"点击{self.form_description}的提交按钮")

# 使用
form = FormComponent(page, "用户注册表单")
await form.fill_field("用户名", "testuser")
await form.fill_field("邮箱", "test@example.com")
await form.select_option("国家", "中国")
await form.submit()
```

## 断言和验证

### AI驱动的断言
```python
from midscene import expect

async def test_assertions():
    # 文本断言
    await expect(page).to_have_text("欢迎回来")
    await expect(page).to_contain_text("登录成功")
    
    # 元素存在性
    await expect(page).to_have_element("用户头像")
    await expect(page).not_to_have_element("错误提示")
    
    # 状态断言
    await expect(page).to_be_enabled("提交按钮")
    await expect(page).to_be_disabled("下一步按钮")
    
    # 数量断言
    count = await page.ai_count("购物车中的商品")
    assert count == 3, f"期望3个商品，实际{count}个"
    
    # 自定义断言
    result = await page.ai_query("页面是否显示成功的绿色勾选图标")
    assert result, "未找到成功标识"
```

### 视觉验证
```python
async def visual_verification():
    # 截图对比
    await page.screenshot("baseline.png")
    
    # 执行操作
    await page.ai_action("切换到深色模式")
    
    # 对比截图
    await page.screenshot("current.png")
    diff = await page.compare_screenshots("baseline.png", "current.png")
    
    assert diff.similarity > 0.95, f"页面变化过大: {diff.percentage}%"
    
    # AI判断视觉变化
    is_dark_mode = await page.ai_query("页面是否为深色主题")
    assert is_dark_mode, "深色模式未生效"
```

## 数据驱动测试

### 参数化测试
```python
import pytest

test_data = [
    ("valid@email.com", "Pass123!", "success"),
    ("invalid-email", "Pass123!", "邮箱格式错误"),
    ("valid@email.com", "123", "密码长度不足"),
    ("", "", "请填写必填项"),
]

@pytest.mark.parametrize("email,password,expected", test_data)
async def test_login_scenarios(email, password, expected):
    page = await setup_page()
    login_page = LoginPage(page)
    
    await login_page.navigate()
    await login_page.login(email, password)
    
    if expected == "success":
        assert await login_page.is_logged_in()
    else:
        error = await login_page.get_error_message()
        assert expected in error
```

### 从文件加载测试数据
```python
import json
import yaml

async def load_test_data(file_path: str):
    """从文件加载测试数据"""
    if file_path.endswith('.json'):
        with open(file_path) as f:
            return json.load(f)
    elif file_path.endswith('.yaml'):
        with open(file_path) as f:
            return yaml.safe_load(f)

# test_data.yaml
"""
login_tests:
  - scenario: 正常登录
    email: test@example.com
    password: Password123!
    expected: success
  - scenario: 错误密码
    email: test@example.com
    password: wrongpass
    expected: 密码错误
"""

async def test_from_yaml():
    data = await load_test_data("test_data.yaml")
    
    for test_case in data["login_tests"]:
        page = await setup_page()
        # 执行测试...
```

## 错误处理和重试

### 智能重试
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def flaky_action(page: Page, action: str):
    """对不稳定的操作进行重试"""
    try:
        await page.ai_action(action, timeout=5000)
    except TimeoutError:
        # 刷新页面重试
        await page.reload()
        raise

# 使用
await flaky_action(page, "点击偶尔加载慢的按钮")
```

### 错误恢复
```python
async def robust_test_flow():
    page = await setup_page()
    
    try:
        await page.ai_action("点击登录按钮")
    except Exception as e:
        # 截图保存错误现场
        await page.screenshot(f"error_{datetime.now().timestamp()}.png")
        
        # 尝试恢复
        if "not found" in str(e):
            # 可能页面未加载完成
            await page.wait_for_load_state("networkidle")
            await page.ai_action("点击登录按钮")
        else:
            raise
```

## 性能优化

### 并行执行
```python
import asyncio

async def run_tests_parallel():
    """并行执行多个测试"""
    tests = [
        test_login(),
        test_registration(),
        test_checkout(),
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"测试{i}失败: {result}")
```

### 资源复用
```python
class BrowserPool:
    """浏览器实例池"""
    
    def __init__(self, size: int = 3):
        self.pool = []
        self.size = size
    
    async def get_page(self) -> Page:
        if len(self.pool) < self.size:
            page = Page()
            self.pool.append(page)
            return page
        
        # 复用现有页面
        page = self.pool.pop(0)
        await page.goto("about:blank")  # 清空页面
        self.pool.append(page)
        return page
    
    async def close_all(self):
        for page in self.pool:
            await page.close()

# 使用
pool = BrowserPool(size=5)
page1 = await pool.get_page()
page2 = await pool.get_page()
```

## 调试技巧

### 调试模式
```python
async def debug_test():
    config = Config(
        headless=False,  # 显示浏览器
        slow_mo=500,  # 每个操作延迟500ms
        devtools=True,  # 打开开发者工具
    )
    
    page = Page(config)
    
    # 暂停执行，等待手动操作
    await page.pause()
    
    # 打印页面信息
    print(await page.title())
    print(await page.url())
```

### 日志记录
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("midscene")

async def logged_action(page: Page, action: str):
    """带日志的操作"""
    logger.info(f"执行操作: {action}")
    
    try:
        result = await page.ai_action(action)
        logger.info(f"操作成功: {action}")
        return result
    except Exception as e:
        logger.error(f"操作失败: {action}, 错误: {e}")
        await page.screenshot(f"error_{action}.png")
        raise
```

## Agent集成

### 从测试用例JSON生成Midscene脚本
```python
def generate_midscene_script(test_case: dict) -> str:
    """将测试用例JSON转换为Midscene脚本"""
    
    script = f'''
async def test_{test_case["id"].lower()}():
    """
    {test_case["title"]}
    优先级: {test_case["priority"]}
    """
    page = await setup_page()
    
    try:
'''
    
    for i, step in enumerate(test_case["steps"], 1):
        action = step["action"]
        data = step.get("data", "")
        
        if "输入" in action:
            script += f'        await page.ai_action("{action}", text="{data}")\n'
        else:
            script += f'        await page.ai_action("{action}")\n'
        
        if "expected" in step:
            script += f'        await expect(page).to_contain_text("{step["expected"]}")\n'
    
    # 添加最终断言
    script += f'''
        # 最终验证
        await expect(page).to_contain_text("{test_case["expected"]}")
        
    finally:
        await page.screenshot("test_{test_case["id"]}.png")
        await page.close()
'''
    
    return script

# 使用
test_case_json = {...}  # 从Agent获取
script = generate_midscene_script(test_case_json)
exec(script)  # 或保存到文件
```
