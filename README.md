# AI 测试用例生成与 UI 自动化平台

基于 `LangGraph + Pydantic + Midscene/Playwright` 的 AI 测试项目。它从 requirement 文档出发，生成测试策略、测试用例、结构化脚本规划，并可执行 UI 自动化与报告输出。

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
```

可选：

```bash
npx playwright install chromium
```

复制环境变量模板：

```bash
copy .env.example .env
```

至少需要补充 LLM 相关配置：

```bash
LLM_KEY=your_api_key
LLM_MODEL=qwen-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 登录凭证

登录 requirement 现在默认优先读取文档里的明文字段，这是本地最省事的方式：

```md
## Credentials
- identifier: your_login_identifier
- password: your_login_password
```

同时继续兼容占位符字段：

```md
## Credentials
- identifier_env: LOGIN_USERNAME
- password_env: LOGIN_PASSWORD
```

如果 requirement 没写明文，就会回退到 `.env` 中的：

```bash
LOGIN_USERNAME=your_login_identifier
LOGIN_PASSWORD=your_login_password
```

仓库里的官方样例仍然只保留占位符，不提交真实账号密码。

## 运行

正式 CLI 入口是 `main_v2.py`，支持 `run`、`validate`、`demo`：

```bash
python main_v2.py run --requirement-file examples/requirement_baidu.md --no-ui
python main_v2.py validate --requirement-file examples/benchmarks/benchmark_list_search.md
python main_v2.py demo --demo-case login-success --no-ui
```

常用参数：

- `--output-dir`: 指定结构化产物输出目录
- `--page-url`: 覆盖 requirement 中的页面地址
- `--max-iterations`: 控制评审回退轮次
- `--clean`: 运行前清理临时脚本、Allure 和 Playwright 产物
- 默认会在 UI 运行结束后自动尝试打开 Allure 报告
- `--no-open-report`: 禁止自动打开 Allure 报告

## 输出

每次运行都会在 `output/runs/<run_id>/` 下生成稳定契约文件：

- `requirements.json`
- `test_strategy.json`
- `test_cases.json`
- `review.json`
- `script_plan.json`
- `execution.json`
- `run_summary.json`
- `run_manifest.json`

如果脚本成功生成，还会附带：

- `generated.spec.ts`

其中：

- `script_plan.json` 会保留 `ScriptExecutionPlan`，明确每一步使用 `playwright_native`、`midscene_ai` 或 `mixed`
- `execution.json` 会包含标准化失败分类，例如 `credential_issue`、`element_location_issue`、`assertion_issue`、`timeout_issue`
- `run_summary.json` 会给出需求数、用例数、预算、执行策略分布和失败摘要

## Benchmark

仓库内置 3 个稳定 benchmark：

- `login-success`
- `form-validation`
- `list-search`

对应文档位于 `examples/benchmarks/`。

## 限制

- `validate` 和 `--no-ui` 模式不会执行浏览器自动化，只验证从 requirement 到结构化产物的链路
- 完整 UI 执行依赖本地 `npx playwright`、Midscene 与正确的模型配置
- 当前优先级是“简历可投、面试可讲、结构化可验证”，暂未扩展到 Web API、前端平台或 RAG
