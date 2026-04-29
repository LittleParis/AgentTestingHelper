---
name: test_executor.json_report_path 修复
description: 修复 json_report_path 未定义导致测试无法执行的 Bug
type: fix-record
---

# test_executor.py json_report_path 未定义修复

## 问题描述

`core/automation/test_executor.py` 第374行使用了未定义的变量 `json_report_path`：

```python
parts = [
    ...
    f"--output={json_report_path}",  # NameError: json_report_path 未定义
]
```

这导致：
- `_build_playwright_command_args()` 抛出 `NameError`
- 测试执行器无法构建正确的命令
- 所有测试都"假运行"，执行时间仅 0.001 秒
- 测试结果全部显示为失败（实际根本没有运行）

## 影响链路分析

- **文件**: `core/automation/test_executor.py`
- **影响范围**: 所有 Playwright 测试执行
- **影响链路**: 运行测试 → 构建命令 → NameError → 测试未执行 → 返回失败结果

## 修复内容

移除未定义的 `--output` 参数（Playwright JSON reporter 默认输出到 stdout）：

```python
# 修复前
parts = [
    ...
    f"--reporter=json",
    f"--output={json_report_path}",  # 移除这行
]

# 修复后
parts = [
    ...
    f"--reporter=json",
]
```

## 涉及方法说明

| 方法 | 说明 |
|------|------|
| `_build_playwright_command_args()` | 构建 Playwright 命令参数列表 |
| `--reporter=json` | Playwright 输出 JSON 格式结果到 stdout |

## 验证结果

```
Command building successful:
npx.cmd playwright test test.spec.ts --config=.../playwright.config.ts --timeout=120000 --retries=0 --reporter=json
```

## 修改文件

- `core/automation/test_executor.py` — 移除未定义的 `--output` 参数
