# Issue #8: playwright cli

| 属性 | 值 |
|------|-----|
| 状态 | 🟢 open |
| 标签 | 无标签 |
| 创建时间 | 2026-04-21 |
| 更新时间 | 2026-04-21 |
| 关闭时间 | 未关闭 |
| 评论数 | 0 |
| 链接 | [https://github.com/LittleParis/AgentTestingHelper/issues/8](https://github.com/LittleParis/AgentTestingHelper/issues/8) |

---

## 内容

# AI 驱动的 Web 全流程自动化测试平台

> 面试讲解用文档 | 项目：UIAutoTest

---

## 一句话介绍

**基于 AI Agent + playwright-cli 的 Web 全流程自动化测试平台，能从需求文档自动生成测试用例、驱动浏览器执行、输出缺陷报告并推送飞书通知，全程零人工干预。**

---

## 项目背景

跨境支付业务官网每次迭代都需要覆盖多站点（Global/HK/CN）、多语言（中/英）、多视口（PC/平板/移动端）的回归测试，人工测试成本高、容易遗漏。这个平台的目标是：**输入需求文档，自动输出测试结论**。

---

## 整体架构（四层）

```
┌─────────────────────────────────────────────────────────┐
│                第一层：AI Agent 调度层                   │
│                                                         │
│  Kiro AI + Steering 文件（test-engineer.md）            │
│  → 定义测试工作流、角色规范、执行标准                    │
│  → 读取需求文档、生成用例、驱动执行、输出报告            │
└────────────────────┬────────────────────────────────────┘
                     ↓ 调用
┌────────────────────────────────────────────────────────┐
│                第二层：Python 工具层（BaseTool）         │
│                                                        │
│  pdf_reader.py          需求文档解析（PDF → 文本）      │
│  test_case_writer.py    生成测试用例/缺陷清单 Excel     │
│  bug_reporter.py        Bug 收集、管理、格式转换        │
│  feishu_notifier.py     飞书机器人通知                  │
│  parallel_test_runner.py 多站点并行测试执行器           │
│  kb_search.py           本地知识库/源码搜索             │
│  feiShuRobot/           Bug 按规则分发到不同飞书群      │
└────────────────────┬───────────────────────────────────┘
                     ↓ 驱动
┌────────────────────────────────────────────────────────┐
│              第三层：playwright-cli 浏览器层            │
│                                                        │
│  open / goto / click / fill / eval / screenshot        │
│  snapshot（获取页面元素快照）                           │
│  state-save / state-load（登录态持久化）                │
│  -s=<session>（多会话并行）                             │
└────────────────────┬───────────────────────────────────┘
                     ↓ 访问
┌────────────────────────────────────────────────────────┐
│                第四层：被测系统（测试环境）              │
│                                                        │
│  global.lianlianpay-inc.com  （Global 站）             │
│  hk.lianlianpay-inc.com      （HK 站）                 │
│  cn.lianlianpay-inc.com      （CN 站）                 │
└────────────────────────────────────────────────────────┘
```

---

## 测试全流程（4 个 Phase）

```
输入：需求文档（PDF）+ 测试环境 URL
         ↓
  Phase 1：需求拆解
  - AI 读取 PDF，提取功能点、字段规则、交互逻辑
  - 输出：需求拆解&测试范围说明书.md
         ↓
  Phase 2：用例生成
  - 生成 8 类用例（正向/逆向/边界/DB/日志/防回归/探索式）
  - 覆盖多站点 × 多语言 × 多视口
  - 输出：测试用例.xlsx
         ↓
  Phase 3：自动回归
  - playwright-cli 逐条执行用例
  - 三层校验：UI 文本 / Kibana 日志 / DB 查询
  - 发现 Bug 立即截图，记录完整复现步骤
  - 输出：截图（BUG_XXX.png）
         ↓
  Phase 4：报告产出
  - 生成缺陷清单.xlsx
  - 生成 Web 测试总结报告.md
  - 推送飞书通知（含完整复现步骤）
```

---

## 核心模块详解

### 1. pdf_reader.py — 需求文档解析
- 使用 **PyMuPDF** 库解析 PDF
- 逐页提取文本，保存到 `case/PDFDocs/`
- AI Agent 读取文本后进行需求分析

### 2. test_case_writer.py — Excel 生成
- 用 **openpyxl** 生成格式化 Excel
- 测试用例表：蓝色表头，10 列（编号/标题/前置条件/步骤/预期结果/优先级等）
- 缺陷清单表：红色表头，9 列（缺陷ID/模块/等级/复现步骤/截图等）

### 3. bug_reporter.py — Bug 管理
- 内存中维护 Bug 列表（`_bugs: List[Dict]`）
- 支持按严重度筛选（P0/P1/P2/P3）
- 可导出为 Excel 格式或飞书格式
- 通过 `send_to_feishu()` 一键推送

### 4. feishu_notifier.py — 飞书通知
- 读取 `.env` 文件获取 Webhook 和签名密钥
- 支持：文本消息 / 富文本消息 / 测试汇总 / Bug 汇总 / 逐条发送
- P0 级 Bug 自动 @所有人

### 5. parallel_test_runner.py — 并行测试
- 用 `ThreadPoolExecutor` 并发启动多个 playwright-cli session
- 每个 session 独立打开浏览器，执行校验，截图
- 汇总所有 session 结果，生成 JSON 报告
- 典型场景：同时测试 Global/HK/CN 三个站点

### 6. feiShuRobot/distribute_bug.py — Bug 分发
- 读取 Bug JSON + YAML 路由规则
- 按 severity/module 路由到不同飞书群
- 支持 dry-run 模式验证路由规则
- 典型场景：P0 发紧急群，P2 发普通群

### 7. kb_search.py — 知识库搜索
- 4 种模式：文件名搜索 / 内容关键词搜索 / 读取文件 / 目录树
- 支持路径别名（简化长路径输入）
- 只处理文本文件（.md/.json/.java/.py 等），不支持 Word/PDF
- AI Agent 用它检索历史需求文档和测试经验

---

## 产出文件结构

```
case/
├── PDFDocs/          需求文档解析结果（.txt）
├── TestPoint/        需求拆解说明书（.md）
├── TestCase/         测试用例（.xlsx）
├── screenshots/      截图（BUG_001.png / homepage_global.png）
├── BugReport/        缺陷清单（.xlsx）+ bugs.json
├── TestReport/       测试总结报告（.md）
├── auth/             登录状态文件（.json）
└── TestExperience/   测试经验库（.md + index.json）
```

---

## 关键技术选型

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| playwright-cli | 浏览器自动化 | 命令行驱动，AI Agent 可直接调用，无需写测试代码 |
| PyMuPDF | PDF 解析 | 速度快，支持中文，纯 Python |
| openpyxl | Excel 生成 | 支持样式定制，无需安装 Office |
| requests | 飞书通知 | 轻量，直接调用飞书 Webhook API |
| ThreadPoolExecutor | 并行测试 | Python 标准库，无额外依赖 |
| Kiro AI + Steering | 测试调度 | 用自然语言定义工作流，AI 自动执行 |

---

## 安全规范（重要）

**禁止在生产环境执行自动化测试！**

| 环境 | 域名特征 | 是否允许 |
|------|----------|----------|
| 测试环境 | `*-inc.com` | ✅ 允许 |
| 生产环境 | `*.lianlianpay.com`（不含 -inc） | ❌ 禁止 |

---

## 实际执行效果（以本次测试为例）

- **需求**：连连国际官网品牌迭代（Logo 替换 + 文字替换 + 数据口径更新）
- **用例数**：29 条（自动生成）
- **执行用例**：13 条 P0 用例
- **执行结果**：13/13 PASS，0 缺陷
- **覆盖范围**：Global + HK 两个站点，首页/公司页/B2B页/登录页
- **耗时**：约 3 分钟（含多站点跳转和截图）

---

## 面试常见问题参考答案

**Q：这个平台和传统 Selenium/Pytest 方案有什么区别？**

A：传统方案需要手写测试代码，维护成本高。这个平台的核心差异是：
1. **零代码**：测试用例由 AI 从需求文档自动生成，不需要手写
2. **自然语言驱动**：playwright-cli 用自然语言指令操作浏览器，AI 可以直接调用
3. **全流程自动化**：从需求解析到报告推送，全程无需人工介入

**Q：如何保证测试覆盖率？**

A：通过三个维度保证：
1. **多站点**：Global/HK/CN 三个站点都覆盖
2. **多语言**：中文和英文两套用例
3. **多视口**：PC（1920x1080）/ 平板（768x1024）/ 移动端（375x812）

**Q：发现 Bug 后如何处理？**

A：强制规范：
1. 发现即截图（`playwright-cli screenshot --filename=BUG_XXX.png`）
2. 记录完整复现步骤（环境 + URL + 操作步骤 + 预期/实际结果）
3. 写入缺陷清单 Excel
4. 通过飞书机器人推送通知（P0 自动 @所有人）

**Q：并行测试是怎么实现的？**

A：playwright-cli 支持 `-s=<session>` 参数创建独立浏览器会话，`parallel_test_runner.py` 用 Python 的 `ThreadPoolExecutor` 并发启动多个 session，每个 session 独立执行测试，最后汇总结果。

**Q：测试经验如何积累和复用？**

A：每次测试结束后，将新发现的测试点、常见问题、最佳实践写入 `case/TestExperience/` 目录（Markdown 格式），下次测试时 AI Agent 通过 `kb_search.py` 检索历史经验，自动补充到测试用例中。

