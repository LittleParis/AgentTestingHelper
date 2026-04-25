# 修复记录索引

本目录记录所有代码修复的详细信息，供后续复盘参考。

---

## 修复记录列表

| 日期 | Issue 编号 | 文件 | 概述 |
|------|------------|------|------|
| 2026-04-24 | Bug | [2026-04-23-test-executor-json-report-path.md](2026-04-23-test-executor-json-report-path.md) | test_executor.py json_report_path 未定义导致测试无法执行 |
| 2026-04-23 | #37 | [2026-04-23-issue-37.md](2026-04-23-issue-37.md) | QUICKSTART.md 环境变量名称和路径修正 |
| 2026-04-23 | #42 | [2026-04-23-issue-42.md](2026-04-23-issue-42.md) | test_analyzer_core.py 改写为标准 pytest 格式 |
| 2026-04-23 | #22 | [2026-04-23-issue-22.md](2026-04-23-issue-22.md) | AllureReporter.open_report 改用 webbrowser 避免进程泄漏 |
| 2026-04-23 | #39 | [2026-04-23-issue-39.md](2026-04-23-issue-39.md) | get_settings 启动时检查 LLM_KEY 是否配置 |
| 2026-04-23 | #32 | [2026-04-23-issue-32.md](2026-04-23-issue-32.md) | pytest.ini 移到根目录，更新 testpaths |
| 2026-04-23 | #26 | [2026-04-23-issue-26.md](2026-04-23-issue-26.md) | generate_allure_from_results.py 移除硬编码，从实际文件读取 |
| 2026-04-23 | #41 | [2026-04-23-issue-41.md](2026-04-23-issue-41.md) | test_workflow.py Mock 路径修复，添加 core. 前缀 |
| 2026-04-22 | #14 | [2026-04-22-issue-14.md](2026-04-22-issue-14.md) | ID 格式正则放宽，支持 1-6 位数字和子用例格式 |
| 2026-04-22 | #28 | [2026-04-22-issue-28.md](2026-04-22-issue-28.md) | TestExecutor 添加 --config 参数，修复相对路径 |
| 2026-04-22 | #27 | [2026-04-22-issue-27.md](2026-04-22-issue-27.md) | conftest.py 移除重复路径拼接，统一使用 project_paths |
| 2026-04-22 | #24 | [2026-04-22-issue-24.md](2026-04-22-issue-24.md) | requirements.txt 补充 langgraph，移除未使用依赖 |
| 2026-04-22 | #17 | [2026-04-22-issue-17.md](2026-04-22-issue-17.md) | playwright.config.ts 移除重复字段，baseURL 改为环境变量 |
| 2026-04-22 | #15 | [2026-04-22-issue-15.md](2026-04-22-issue-15.md) | 移除 TestCase.title 数字开头限制 |
| 2026-04-22 | #13 | [2026-04-22-issue-13.md](2026-04-22-issue-13.md) | 删除废弃的 requirement_analyzer_v2.py |
| 2026-04-22 | #9 | [2026-04-22-issue-9.md](2026-04-22-issue-9.md) | TestExecutor 改用 JSON reporter + 清理死代码 |
| 2026-04-22 | #8 | [2026-04-22-issue-8.md](2026-04-22-issue-8.md) | Midscene action 转换改用 LLM |
| 2026-04-21 | #1, #2, #7 | [2026-04-21-issue-1-2-7.md](2026-04-21-issue-1-2-7.md) | 结构化输出、评审反馈注入、重试机制 |

---

## Issue 概览

### Issue #14：ID 格式正则限制过严
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：LLM 生成的 ID 不再触发验证失败，支持子用例格式

### Issue #28：package.json 放错目录导致 npx 找不到配置
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：TestExecutor 能正确找到 Playwright 配置，测试执行链路正常

### Issue #27：conftest.py OUTPUT_DIR 变量遮蔽
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：消除路径不一致问题，统一使用 project_paths 的绝对路径

### Issue #24：requirements.txt 缺少依赖且有未使用依赖
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：补充缺失的 langgraph，移除 3 个未使用依赖，放宽版本限制

### Issue #17：playwright.config.ts 重复字段和错误 baseURL
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：消除重复配置，baseURL 可通过环境变量灵活配置

### Issue #15：TestCase.title 不合理的数字开头限制
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：LLM 生成的标题不再触发验证失败

### Issue #13：requirement_analyzer_v2.py 是废弃文件
- **状态**：✅ 已修复
- **日期**：2026-04-22
- **收益**：删除损坏的废弃代码，消除混淆

### Issue #1：结构化输出替换手动 JSON 解析
- **状态**：✅ 已修复
- **日期**：2026-04-21
- **收益**：消除约 150 行重复代码，解析失败率大幅降低

### Issue #2：评审反馈注入生成器
- **状态**：✅ 已修复
- **日期**：2026-04-21
- **收益**：迭代有实际意义，第二次生成质量明显高于第一次

### Issue #7：LLMClient 重试机制和 Token 追踪
- **状态**：✅ 已修复
- **日期**：2026-04-21
- **收益**：网络抖动自动重试，Token 消耗可追踪

---

## 待修复 Issue

参见 [原始 Issue 列表](../issues/issue-02.md)，按优先级处理。
