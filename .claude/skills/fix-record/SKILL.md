# Fix Record Skill

记录代码修复的 skill。**当单元测试通过后自动触发**，创建修复记录文档供后续复盘。

## 触发条件

**自动触发**：当满足以下所有条件时，自动执行此 skill：
1. 完成了代码修复
2. 运行了单元测试
3. 单元测试全部通过

**手动触发**：用户说"记录修复"、"写修复文档"时

## 工作流程

```
修复代码 → 运行单元测试 → 测试通过 → 触发此 skill → 创建修复记录
```

## 规则

### 1. 修复记录格式

每次修复完成后，创建或更新 `docs/fix-records/` 目录下的 Markdown 文件：

**文件命名规则**：`YYYY-MM-DD-issue-{编号列表}.md`

例如：
- `2026-04-21-issue-1-2-7.md` — 修复了 Issue #1, #2, #7
- `2026-04-22-issue-8.md` — 修复了 Issue #8

### 2. 文档内容结构

每个修复记录必须包含：

```markdown
# Issue #{编号列表} 修复记录

> 修复日期：YYYY-MM-DD
> 修复人：Claude Code

---

## Issue #{编号}：{标题}

### 问题描述
{问题的详细描述，来自原始 issue 文档}

### 修复方案
{修复的具体方案，包含代码示例}

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| {文件路径} | {修改说明} |

### 单元测试结果
{测试命令和实际输出}

---

## 总结
| Issue | 标题 | 状态 | 单元测试 |
|-------|------|------|----------|
| #N | {标题} | ✅ 已修复 | X/X 通过 |
```

### 3. 执行步骤

单元测试通过后，**必须**执行：

1. **确认测试结果** — 记录实际的测试输出（通过/失败数量）
2. **创建修复记录** — 在 `docs/fix-records/` 下创建文档
3. **更新索引** — 在 `docs/fix-records/README.md` 中添加新记录

### 4. 文档位置

```
docs/
├── fix-records/
│   ├── README.md                    # 索引文件
│   ├── 2026-04-21-issue-1-2-7.md    # 修复记录
│   └── 2026-04-22-issue-8.md        # 修复记录
└── issues/
    └── issue-02.md                  # 原始 Issue 列表
```

## 示例

### 场景：修复 Issue #8 后单元测试通过

```
[修复代码]
→ 修改 core/automation/midscene_generator.py

[运行测试]
→ pytest tests/unit/test_midscene_generator.py -v
→ 5 passed in 2.34s

[自动触发此 skill]
→ 创建 docs/fix-records/2026-04-22-issue-8.md
→ 更新 docs/fix-records/README.md
```

### 生成的文档内容

```markdown
# Issue #8 修复记录

> 修复日期：2026-04-22
> 修复人：Claude Code

---

## Issue #8：MidsceneScriptGenerator action 转换逻辑脆弱

### 问题描述
`_convert_action_to_ai_prompt()` 用大量 `if "关键词" in action` 的字符串匹配...

### 修复方案
将 action 转换交给 LLM 处理...

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| core/automation/midscene_generator.py | 重写 action 转换逻辑 |

### 单元测试结果
```
pytest tests/unit/test_midscene_generator.py -v
============================= 5 passed in 2.34s ==============================
```

---

## 总结
| Issue | 标题 | 状态 | 单元测试 |
|-------|------|------|----------|
| #8 | MidsceneScriptGenerator action 转换逻辑脆弱 | ✅ 已修复 | 5/5 通过 |
```

## 注意事项

1. **测试必须真实通过** — 不得伪造测试结果
2. **记录实际输出** — 包含真实的测试命令和输出
3. **代码示例要完整** — 包含修复前后的对比代码
4. **文件路径要准确** — 便于后续追溯
5. **日期格式统一** — 使用 `YYYY-MM-DD` 格式
