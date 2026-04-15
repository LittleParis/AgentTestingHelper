# 阶段3.1 Midscene 环境搭建 - 复盘文档

**日期**: 2026-04-11
**阶段**: 3.1 Midscene 环境搭建 + Demo
**状态**: ✅ 完成

---

## 一、目标

搭建 Midscene.js 开发环境，验证 AI 驱动的元素定位能力，为后续自动化测试脚本生成奠定基础。

---

## 二、完成的工作

### 2.1 创建的文件

| 文件 | 用途 |
|------|------|
| `package.json` | Node.js 项目配置，定义依赖 |
| `playwright.config.ts` | Playwright 测试框架配置 |
| `tsconfig.json` | TypeScript 编译配置 |
| `.env` | 新增 Midscene 相关环境变量 |
| `tests/generated/midscene-demo.spec.ts` | Midscene Demo 测试文件 |
| `tests/midscene.config.ts` | Midscene 配置文件（备用） |
| `browsers/chromium-1217/` | Chromium 浏览器目录 |

### 2.2 安装的依赖

```json
{
  "dependencies": {
    "@midscene/web": "^0.15.0",
    "@playwright/test": "^1.48.0",
    "playwright": "^1.48.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "allure-playwright": "^3.7.1",
    "dotenv": "^16.0.0",
    "typescript": "^5.6.0"
  }
}
```

### 2.3 配置的环境变量

```bash
# Midscene AI 配置
OPENAI_API_KEY=dc48c897fe2b3992a5cad21f360dc32d:ZWQzNWJhNmYxOWM0MjY0YjA5YjUyNWQy
OPENAI_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2
MIDSCENE_MODEL_NAME=astron-code-latest
```

### 2.4 验证结果

```
ok 1 AI定位演示: 用户登录流程 (24.3s)
ok 2 AI定位演示: 完成待办事项 (36.0s)
2 passed (1.1m)
```

---

## 三、遇到的困难与解决方案

### 困难 1：C 盘空间不足

**问题描述**：
- Node.js Playwright 默认将浏览器下载到 `C:\Users\{user}\AppData\Local\ms-playwright\`
- 用户 C 盘空间不足，无法下载约 180MB 的 Chromium 浏览器

**解决方案**：
- 设置环境变量 `PLAYWRIGHT_BROWSERS_PATH` 指向项目目录
- 浏览器下载到 `G:\桌面\AgentTest\browsers\` 目录

```bash
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright install chromium
```

---

### 困难 2：浏览器下载速度慢

**问题描述**：
- Playwright 浏览器从国外 CDN 下载（`cdn.playwright.dev`）
- 国内下载速度极慢，长时间卡在 0%-20%

**解决方案**：
- 开启 VPN（台湾节点）加速下载
- 或者手动下载 ZIP 文件并解压到指定目录

**手动下载地址**：
```
https://cdn.playwright.dev/builds/cft/147.0.7727.15/win64/chrome-win64.zip
```

**解压目录**：
```
G:\桌面\AgentTest\browsers\chromium-1217\chrome-win64\
```

---

### 困难 3：Python Playwright 与 Node.js Playwright 版本不兼容

**问题描述**：
- Python Playwright 版本：1.48.0
- Node.js Playwright 版本：1.59.1
- 浏览器版本不同，无法复用已安装的浏览器

**解决方案**：
- 放弃复用 Python Playwright 浏览器的想法
- 单独下载 Node.js Playwright 对应版本的 Chromium

---

### 困难 4：解压目录嵌套错误

**问题描述**：
- 手动解压 ZIP 文件时，目录结构多嵌套了几层
- 导致 Playwright 找不到 `chrome.exe`

**错误结构**：
```
browsers/chromium-1217/chrome-win64/chrome-win64/chrome-win64/chrome.exe
```

**正确结构**：
```
browsers/chromium-1217/chrome-win64/chrome.exe
```

**解决方案**：
```bash
mv /g/桌面/AgentTest/browsers/chromium-1217/chrome-win64/chrome-win64/chrome-win64/* /g/桌面/AgentTest/browsers/chromium-1217/chrome-win64/
rm -rf /g/桌面/AgentTest/browsers/chromium-1217/chrome-win64/chrome-win64
```

---

### 困难 5：缺少 ffmpeg 依赖

**问题描述**：
- Playwright 配置了 `video: 'retain-on-failure'`
- 运行测试时报错缺少 ffmpeg

**错误信息**：
```
Executable doesn't exist at G:\桌面\AgentTest\browsers\ffmpeg-1011\ffmpeg-win64.exe
```

**解决方案**：
- 在 `playwright.config.ts` 中禁用视频录制
```typescript
use: {
  video: 'off',  // 禁用视频录制，避免需要 ffmpeg
}
```

---

### 困难 6：Midscene AI 模型配置失败

**问题描述**：
- Midscene 需要配置 AI 模型才能工作
- 初始运行报错：`Cannot find config for AI model service`

**尝试的方案**：

1. ❌ 在测试文件中使用 `dotenv` 加载 `.env`
   - 问题：Playwright worker 进程中环境变量未正确传递

2. ❌ 使用 `overrideAIConfig()` 函数
   - 问题：配置未生效

3. ✅ 在 `playwright.config.ts` 中加载 `.env`
   - 成功：环境变量正确传递给所有 worker

**最终解决方案**：
```typescript
// playwright.config.ts
import { config } from 'dotenv';
config(); // 在配置文件顶部加载 .env
```

---

### 困难 7：Midscene Fixture 导入方式错误

**问题描述**：
- 按照官方文档导入 `test`，但运行时报错

**错误代码**：
```typescript
import { test } from '@midscene/web/playwright';
// Error: Cannot read properties of undefined (reading 'describe')
```

**解决方案**：
- 使用 `base.extend()` 方式扩展 Playwright test
```typescript
import { test as base } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';

const test = base.extend<{ ai: any }>(PlaywrightAiFixture());
```

---

### 困难 8：测试超时

**问题描述**：
- AI 操作需要调用远程 LLM，耗时较长
- 默认 30 秒超时不够用

**解决方案**：
- 在 `playwright.config.ts` 中增加超时时间
```typescript
export default defineConfig({
  timeout: 60000,  // 每个测试最长 60 秒
  use: {
    actionTimeout: 10000,  // 每个操作最长 10 秒
  },
});
```

---

## 四、关键经验总结

### 4.1 环境变量加载时机

Playwright 测试在独立的 worker 进程中运行，需要确保环境变量在配置文件加载时就已经可用。

**推荐做法**：
```typescript
// playwright.config.ts 顶部
import { config } from 'dotenv';
config();
```

### 4.2 浏览器路径配置

当 C 盘空间不足时，可以通过环境变量指定浏览器下载路径：

```bash
# 临时设置（当前终端有效）
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright test

# 永久设置（添加到系统环境变量）
export PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers"
```

### 4.3 Midscene 与自定义 LLM

Midscene 支持任何 OpenAI 兼容的 API，只需配置：
- `OPENAI_API_KEY` - API 密钥
- `OPENAI_BASE_URL` - API 端点
- `MIDSCENE_MODEL_NAME` - 模型名称

### 4.4 VPN 对下载速度的影响

| 场景 | 下载速度 |
|------|----------|
| 无 VPN | 极慢（几 KB/s） |
| VPN（台湾节点） | 正常（MB/s 级别） |

---

## 五、下一步计划

| 阶段 | 任务 | 状态 |
|------|------|------|
| 3.1 | Midscene 环境搭建 + Demo | ✅ 完成 |
| 3.2 | 实现 `MidsceneScriptGenerator` | 📋 待开始 |
| 3.3 | 实现 `TestExecutor` | 📋 待开始 |
| 3.4 | 集成到 LangGraph 工作流 | 📋 待开始 |
| 3.5 | Allure 报告集成 | 📋 待开始 |

---

## 六、运行命令备忘

```bash
# 进入项目目录
cd "G:\桌面\AgentTest"

# 运行 Midscene 测试
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright test --headed

# 运行单个测试文件
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright test tests/generated/midscene-demo.spec.ts --headed

# 查看 Playwright 版本
PLAYWRIGHT_BROWSERS_PATH="G:/桌面/AgentTest/browsers" npx playwright --version
```

---

## 七、参考资料

- [Midscene.js 官方文档](https://midscenejs.com)
- [Midscene 模型配置](https://midscenejs.com/model-provider.html)
- [Playwright 配置文档](https://playwright.dev/docs/test-configuration)
- [阶段3设计文档](./PHASE3_DESIGN.md)
