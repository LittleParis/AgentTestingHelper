# Fix Record Skill

记录代码修复的 skill。

## 触发条件

**自动触发**：当满足以下任一条件时，自动执行此 skill：
1. 完成了代码修复 + 运行了单元测试 + 单元测试全部通过
2. 用户说"记录修复"、"写修复文档"、"写个记录"

**建议触发**：当用户说以下内容时，建议使用此 skill：
- "完成了"、"搞定了"、"修好了"
- "git一下"（在推送前先记录修复）
- "总结一下这次修改"

## 工作流程

```
修复代码 → 运行单元测试 → 测试通过 → 触发此 skill → 创建修复记录
     ↓
   遇到问题 → 记录问题 → 继续修复 → 最终通过
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

### 影响链路分析
{如果不修复此 bug，会影响哪些链路的执行}

**受影响的执行链路：**
1. **链路名称** — 具体影响说明
2. **链路名称** — 具体影响说明

**影响范围：** {全局/模块级/单点}

### 修复方案
{修复的具体方案，包含代码示例}

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| {文件路径} | {修改说明} |

### 涉及方法说明
{修复 bug 涉及的方法在项目中的作用}

| 方法名 | 所在文件 | 作用说明 |
|--------|----------|----------|
| `{方法名}` | `{文件路径}` | {方法在项目中的作用} |

**示例：**
```python
# 方法调用示例
{展示方法如何被调用的代码示例}
```

### 单元测试结果
{测试命令和实际输出}

---

## 遇到的问题（如有）

| 序号 | 问题描述 | 原因分析 | 解决方案 |
|------|----------|----------|----------|
| 1 | {问题描述} | {原因} | {如何解决} |

---

## 总结
| Issue | 标题 | 状态 | 单元测试 |
|-------|------|------|----------|
| #N | {标题} | ✅ 已修复 | X/X 通过 |
```

### 3. 问题记录格式

在修复过程中遇到的问题，按以下格式记录：

```markdown
## 遇到的问题

### 问题 1：{简短标题}

**现象**：
```
{错误信息、异常输出、测试失败信息}
```

**原因分析**：
{分析问题产生的原因}

**解决方案**：
{如何解决这个问题，包含代码修改}

**耗时**：约 X 分钟
```

### 4. 执行步骤

单元测试通过后，**必须**执行：

1. **确认测试结果** — 记录实际的测试输出（通过/失败数量）
2. **记录遇到的问题** — 如果修复过程中遇到问题，记录问题详情
3. **创建修复记录** — 在 `docs/fix-records/` 下创建文档
4. **更新索引** — 在 `docs/fix-records/README.md` 中添加新记录

### 5. 文档位置

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

### 场景：修复过程中遇到问题

```
[修复代码]
→ 修改 core/automation/test_executor.py

[运行测试]
→ pytest tests/unit/test_test_executor.py -v
→ 1 failed, 15 passed  ← 测试失败

[记录问题]
→ 问题：f-string 语法错误
→ 原因：f-string 表达式不能包含反斜杠
→ 解决：改用字符串拼接

[重新运行测试]
→ pytest tests/unit/test_test_executor.py -v
→ 16 passed in 0.99s

[自动触发此 skill]
→ 创建修复记录，包含遇到的问题
```

### 生成的文档内容（包含问题记录）

```markdown
# Issue #8 修复记录

> 修复日期：2026-04-22
> 修复人：Claude Code

---

## Issue #8：MidsceneScriptGenerator action 转换逻辑脆弱

### 问题描述
`_convert_action_to_ai_prompt()` 用大量 `if "关键词" in action` 的字符串匹配...

### 影响链路分析

**受影响的执行链路：**
1. **测试脚本生成链路** — action 转换失败会导致生成的 Midscene 脚本无法执行
2. **端到端测试链路** — 脚本执行失败，Allure 报告显示用例不通过
3. **评审迭代链路** — 执行失败触发重新生成，但问题依旧存在

**影响范围：** 模块级（影响所有 UI 自动化测试用例的生成）

### 修复方案
将 action 转换交给 LLM 处理...

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| core/automation/midscene_generator.py | 重写 action 转换逻辑 |

### 涉及方法说明

| 方法名 | 所在文件 | 作用说明 |
|--------|----------|----------|
| `_convert_action_to_ai_prompt()` | `midscene_generator.py` | 将自然语言测试步骤转换为 Midscene AI 指令 |
| `_convert_expected_to_ai_prompt()` | `midscene_generator.py` | 将预期结果转换为 Midscene 验证指令 |
| `generate_script()` | `midscene_generator.py` | 主入口，生成完整的 Midscene 测试脚本 |

**示例：**
```python
# 方法调用示例
generator = MidsceneScriptGenerator()
script = generator.generate_script(test_case, page_url="https://www.baidu.com")

# _convert_action_to_ai_prompt 被内部调用
# 输入: "在搜索框输入关键词"
# 输出: '在搜索框中输入 "关键词"'
```

### 单元测试结果
```
pytest tests/unit/test_midscene_generator.py -v
============================= 16 passed in 0.99s ==============================
```

---

## 遇到的问题

### 问题 1：f-string 语法错误

**现象**：
```
SyntaxError: f-string expression part cannot include a backslash
```

**原因分析**：
Python f-string 表达式中不能直接使用反斜杠，如 `f'{step["key"]}'` 中如果 key 包含特殊字符会导致问题。

**解决方案**：
改用字符串拼接代替 f-string：
```python
# 修复前
verify_text = f'验证: {step["verify_prompt"]}'

# 修复后
verify_prompt = step["verify_prompt"]
verify_text = "验证: " + verify_prompt
```

**耗时**：约 5 分钟

---

## 总结
| Issue | 标题 | 状态 | 单元测试 |
|-------|------|------|----------|
| #8 | MidsceneScriptGenerator action 转换逻辑脆弱 | ✅ 已修复 | 16/16 通过 |
```

## 注意事项

1. **测试必须真实通过** — 不得伪造测试结果
2. **记录实际输出** — 包含真实的测试命令和输出
3. **代码示例要完整** — 包含修复前后的对比代码
4. **文件路径要准确** — 便于后续追溯
5. **日期格式统一** — 使用 `YYYY-MM-DD` 格式
6. **问题记录要详细** — 包含现象、原因、解决方案，便于后续复盘
7. **问题记录可选** — 如果修复过程顺利，可省略问题记录部分
8. **影响链路分析必填** — 说明不修复此 bug 会影响哪些链路执行
9. **涉及方法说明必填** — 说明修复涉及的方法在项目中的作用，并举例
10. **影响范围分级** — 全局（影响整个系统）、模块级（影响某个模块）、单点（影响单个功能）
