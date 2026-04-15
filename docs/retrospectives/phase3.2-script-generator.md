# 阶段3.2 MidsceneScriptGenerator 实现 - 复盘文档

**日期**: 2026-04-11
**阶段**: 3.2 MidsceneScriptGenerator 实现
**状态**: ✅ 完成

---

## 一、目标

实现 `MidsceneScriptGenerator`，将测试用例（JSON格式）自动转换为 Midscene + Playwright 测试脚本（TypeScript）。

---

## 二、完成的工作

### 2.1 创建的文件

| 文件 | 用途 |
|------|------|
| `automation/midscene_generator.py` | Midscene 脚本生成器核心模块 |
| `tests/test_midscene_generator.py` | 生成器测试脚本 |

### 2.2 核心功能

```
测试用例 JSON → MidsceneScriptGenerator → 可执行的 .spec.ts 脚本
```

### 2.3 输入输出示例

**输入** (测试用例 JSON):
```json
{
  "id": "TC_001",
  "title": "用户正常登录",
  "priority": "high",
  "steps": [
    {"action": "输入用户名", "data": "admin"},
    {"action": "输入密码", "data": "password123"},
    {"action": "点击登录按钮", "data": "N/A"}
  ],
  "expected": "登录成功",
  "tags": ["smoke"]
}
```

**输出** (TypeScript 测试脚本):
```typescript
test('TC_001: 用户正常登录', async ({ page, ai }) => {
  // 优先级: high
  // 标签: smoke
  await page.goto(`https://example.com/login`);

  // 步骤: 输入用户名
  await ai(`在邮箱或用户名输入框中输入 "admin"`);

  // 步骤: 输入密码
  await ai(`在密码输入框中输入 "password123"`);

  // 步骤: 点击登录按钮
  await ai(`点击登录按钮`);

  // 最终验证
  await ai(`验证: 操作成功`);
});
```

### 2.4 主要方法

| 方法 | 功能 |
|------|------|
| `generate()` | 从测试用例列表生成脚本 |
| `generate_from_json_file()` | 从 JSON 文件生成脚本 |
| `_convert_action_to_ai_prompt()` | 将操作转换为 Midscene AI 指令 |
| `_convert_expected_to_ai_prompt()` | 将预期结果转换为验证指令 |

---

## 三、遇到的困难与解决方案

### 困难 1：TypeScript 装饰器语法错误

**问题描述**：
- 初始使用 `@allure.title()` 等装饰器语法
- Playwright test 不支持装饰器放在 `test.describe` 内部

**解决方案**：
- 移除装饰器语法
- 使用注释方式记录优先级和标签信息

---

### 困难 2：字符串引号嵌套问题

**问题描述**：
- 生成的 AI 指令包含数据（如邮箱地址）
- 数据中包含 `@` 符号，与单引号冲突
```typescript
// 错误示例
await ai('在邮箱输入框中输入 'test@example.com'');
```

**解决方案**：
- 使用模板字符串（反引号）包裹 AI 指令
```typescript
// 正确示例
await ai(`在邮箱输入框中输入 "test@example.com"`);
```

---

### 困难 3：Playwright 标签语法错误

**问题描述**：
```typescript
// 错误语法
test('TC_001', { tag: ["smoke"] }, async ({ page, ai }) => {...}
// Error: details.tag: does not match any of the expected types
```

**解决方案**：
- 暂时移除标签语法
- 使用注释方式记录标签信息
```typescript
test('TC_001', async ({ page, ai }) => {
  // 标签: smoke
  ...
});
```

---

### 困难 4：浏览器目录被清理

**问题描述**：
- 运行测试时发现 `browsers/chromium-1217/` 目录为空
- 需要重新下载浏览器

**解决方案**：
- 重新执行 `npx playwright install chromium`
- 建议将 `browsers/` 目录添加到 `.gitignore`

---

## 四、关键经验总结

### 4.1 TypeScript 字符串处理

在生成 TypeScript 代码时，优先使用模板字符串（反引号）：
- 避免引号嵌套问题
- 支持多行字符串
- 更容易处理特殊字符

### 4.2 Playwright 测试语法

Playwright test 的标签语法需要特定配置，简化方案：
- 使用注释记录元信息
- 通过 Allure 报告添加额外信息

### 4.3 AI 指令设计

Midscene AI 指令应该：
- 简洁明了
- 避免过于复杂的描述
- 使用中文描述更符合项目需求

---

## 五、下一步计划

| 阶段 | 任务 | 状态 |
|------|------|------|
| 3.1 | Midscene 环境搭建 + Demo | ✅ 完成 |
| 3.2 | 实现 MidsceneScriptGenerator | ✅ 完成 |
| 3.3 | 实现 TestExecutor | 📋 待开始 |
| 3.4 | 集成到 LangGraph 工作流 | 📋 待开始 |
| 3.5 | Allure 报告集成 | 📋 待开始 |

---

## 六、运行命令备忘

```bash
# 测试生成器
cd "G:\桌面\AgentTest"
.venv/Scripts/python tests/test_midscene_generator.py

# 运行生成的测试脚本
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright test tests/generated/auto_generated_*.spec.ts --headed

# 重新下载浏览器
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright install chromium
```

---

## 七、参考资料

- [Midscene.js 官方文档](https://midscenejs.com)
- [Playwright Test 语法](https://playwright.dev/docs/test-annotations)
- [阶段3设计文档](../PHASE3_DESIGN.md)
- [阶段3.1复盘](./phase3.1-midscene-setup.md)
