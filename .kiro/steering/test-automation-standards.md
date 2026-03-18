---
inclusion: fileMatch
fileMatchPattern: "**/tests/**/*.py,**/automation/**/*.py,**/*test*.py"
---

# 测试自动化开发标准

## Midscene UI自动化规范

### 脚本结构
```python
from midscene import Page, expect

async def test_user_login():
    """测试用户登录功能"""
    page = Page()
    
    # 1. 导航
    await page.goto("https://example.com/login")
    
    # 2. 操作（使用AI视觉定位）
    await page.ai_action("输入用户名", text="test@example.com")
    await page.ai_action("输入密码", text="password123")
    await page.ai_action("点击登录按钮")
    
    # 3. 断言
    await expect(page).to_have_text("欢迎回来")
    
    # 4. 清理
    await page.close()
```

### 最佳实践
- 使用描述性的AI指令（"点击蓝色的提交按钮"而不是"点击按钮"）
- 每个操作后添加适当的等待
- 失败时自动截图：`await page.screenshot("failure.png")`
- 使用页面对象模式封装复杂页面
- 测试数据参数化，避免硬编码

### 错误处理
```python
try:
    await page.ai_action("点击登录", timeout=5000)
except TimeoutError:
    await page.screenshot("login_timeout.png")
    raise
```

## Allure报告集成

### 装饰器使用
```python
import allure

@allure.feature("用户管理")
@allure.story("用户登录")
@allure.severity(allure.severity_level.CRITICAL)
async def test_login():
    with allure.step("打开登录页面"):
        await page.goto("/login")
    
    with allure.step("输入凭证"):
        await page.ai_action("输入用户名", text="test")
    
    # 附加截图
    allure.attach(
        await page.screenshot(),
        name="登录页面",
        attachment_type=allure.attachment_type.PNG
    )
```

### 报告增强
- 每个测试用例附加：需求ID、优先级、执行时间
- 失败用例附加：错误日志、页面截图、DOM快照
- 添加环境信息：浏览器版本、操作系统、测试环境URL

## Agent生成的测试代码规范

### 命名约定
- 测试函数：`test_<功能>_<场景>`
- 测试类：`Test<功能模块>`
- 测试文件：`test_<模块名>.py`

### 注释要求
```python
async def test_checkout_with_coupon():
    """
    测试用例ID: TC_CHECKOUT_001
    需求ID: REQ_PAYMENT_003
    描述: 验证使用优惠券结账流程
    前置条件: 用户已登录，购物车有商品
    优先级: High
    """
    pass
```

### 数据驱动测试
```python
import pytest

@pytest.mark.parametrize("username,password,expected", [
    ("valid@test.com", "Pass123!", "success"),
    ("invalid@test.com", "wrong", "error"),
    ("", "", "validation_error"),
])
async def test_login_scenarios(username, password, expected):
    # Agent生成的测试应支持多场景
    pass
```

## 测试用例质量标准

### 必须包含
- 明确的测试目标
- 详细的操作步骤
- 清晰的预期结果
- 测试数据（正常值、边界值、异常值）
- 前置条件和后置清理

### 避免
- 过度依赖sleep等待（使用智能等待）
- 硬编码的选择器（使用AI视觉定位）
- 没有断言的测试
- 过长的测试（拆分为多个小测试）
- 测试间的依赖关系

## 执行策略

### 并行执行
```python
# pytest.ini
[pytest]
addopts = -n auto --dist loadfile
```

### 失败重试
```python
@pytest.mark.flaky(reruns=2, reruns_delay=1)
async def test_flaky_feature():
    pass
```

### 标签分类
```python
@pytest.mark.smoke  # 冒烟测试
@pytest.mark.regression  # 回归测试
@pytest.mark.slow  # 慢速测试
```
