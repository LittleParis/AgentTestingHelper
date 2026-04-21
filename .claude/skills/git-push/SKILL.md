# Git Push Skill

当用户说"git一下"、"推送到git"、"提交代码"时，自动执行 git 推送流程。

## 触发条件

**触发关键词**：
- "git一下"
- "推送到git"
- "提交代码"
- "push一下"
- "git push"

## 工作流程

```
用户说"git一下" → 检查状态 → 添加文件 → 创建commit → 推送到远程
```

## 执行步骤

### 1. 检查 Git 状态

```bash
git status
git diff --stat
git log -3 --oneline
```

### 2. 添加修改的文件

```bash
git add <修改的文件>
```

**注意**：
- 不使用 `git add .` 或 `git add -A`，避免添加意外文件
- 只添加实际修改的相关文件
- 排除 `.env`、`__pycache__/`、`node_modules/` 等

### 3. 创建 Commit

```bash
git commit -m "$(cat <<'EOF'
{commit message}

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

**Commit Message 格式**：
- 使用中文
- 简洁描述修改内容
- 格式：`类型: 简短描述`
  - `feat:` 新功能
  - `fix:` 修复 bug
  - `refactor:` 重构
  - `docs:` 文档更新
  - `test:` 测试相关

### 4. 推送到远程

```bash
git push origin {current-branch}
```

## 示例

### 场景：修复 Issue #7 后推送

```
用户: git一下

[检查状态]
→ git status
→ modified: core/utils/llm_client.py
→ modified: core/models/config.py
→ new file: tests/unit/test_llm_client_retry.py

[添加文件]
→ git add core/utils/llm_client.py core/models/config.py tests/unit/test_llm_client_retry.py

[创建 Commit]
→ git commit -m "feat: LLMClient 重试机制和 Token 追踪

- 添加指数退避重试机制
- 添加 TokenTracker 追踪 Token 消耗
- 实现 LLMClient 单例模式
- 添加 11 个单元测试

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"

[推送]
→ git push origin update-test-platform
```

## 注意事项

1. **检查分支** — 确认当前分支名称
2. **避免敏感文件** — 不提交 `.env`、密钥文件等
3. **确认推送** — 如果是推送到 main/master 分支，先确认用户意图
4. **处理冲突** — 如果有冲突，提示用户手动解决

## 排除文件列表

以下文件不自动添加：
- `.env` / `.env.local`
- `__pycache__/`
- `*.pyc`
- `node_modules/`
- `.mcp.json`（包含敏感信息）
- `allure-results/`
- `allure-report/`
- `output/`
- `temp/`
