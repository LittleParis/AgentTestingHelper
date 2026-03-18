---
inclusion: fileMatch
fileMatchPattern: "**/agents/**/*.py,**/prompts/**/*"
---

# Agent Prompt模板标准

## 需求分析Agent Prompt模板

```python
REQUIREMENT_ANALYSIS_PROMPT = """
你是一个专业的需求分析专家。请分析以下需求文档，提取关键信息。

需求文档内容：
{document_content}

请按以下JSON格式输出：
{{
  "requirements": [
    {{
      "id": "REQ_001",
      "title": "需求标题",
      "description": "详细描述",
      "priority": "high|medium|low",
      "type": "functional|non-functional",
      "acceptance_criteria": ["验收标准1", "验收标准2"],
      "dependencies": ["REQ_002"],
      "business_rules": ["业务规则"],
      "ui_elements": ["涉及的UI元素"]
    }}
  ],
  "summary": "需求概述",
  "risks": ["潜在风险"]
}}

分析要点：
1. 识别所有功能点和非功能需求
2. 提取验收标准（这将用于生成测试用例）
3. 识别业务规则和约束条件
4. 标注优先级和依赖关系
5. 识别UI交互元素（用于UI自动化）
"""
```

## 测试用例生成Agent Prompt模板

```python
TEST_CASE_GENERATION_PROMPT = """
你是一个资深测试工程师。基于以下需求，生成全面的测试用例。

需求信息：
{requirement_json}

测试策略：
- 正常流程测试
- 边界值测试
- 异常场景测试
- 兼容性测试（如适用）

输出格式（JSON）：
{{
  "test_cases": [
    {{
      "id": "TC_001",
      "requirement_id": "REQ_001",
      "title": "测试用例标题",
      "priority": "critical|high|medium|low",
      "type": "functional|ui|integration|performance",
      "preconditions": ["前置条件"],
      "steps": [
        {{
          "step_number": 1,
          "action": "操作描述（用自然语言，适合Midscene AI执行）",
          "data": "测试数据",
          "expected": "预期结果"
        }}
      ],
      "test_data": {{
        "input": {{}},
        "expected_output": {{}}
      }},
      "tags": ["smoke", "regression"],
      "estimated_time": "2分钟"
    }}
  ],
  "coverage_analysis": "覆盖率分析",
  "suggestions": ["优化建议"]
}}

重要提示：
1. 步骤描述要清晰，适合AI视觉定位（如"点击蓝色的登录按钮"）
2. 包含正向和负向测试用例
3. 考虑边界值（空值、最大值、特殊字符）
4. 每个用例应该独立可执行
5. 预期结果要具体可验证
"""
```

## 测试策略Agent Prompt模板

```python
TEST_STRATEGY_PROMPT = """
你是测试架构师。基于需求和历史数据，制定测试策略。

输入信息：
需求：{requirements}
历史缺陷数据：{historical_bugs}
项目约束：{constraints}

输出格式：
{{
  "test_strategy": {{
    "scope": "测试范围",
    "approach": "测试方法",
    "priorities": [
      {{
        "area": "功能区域",
        "priority": "high",
        "rationale": "原因"
      }}
    ],
    "risk_areas": ["高风险区域"],
    "test_types": {{
      "functional": "70%",
      "ui": "20%",
      "integration": "10%"
    }},
    "execution_plan": {{
      "phase1_smoke": ["TC_001", "TC_002"],
      "phase2_regression": ["TC_003"],
      "phase3_exploratory": "探索性测试重点"
    }},
    "resource_estimate": "预估工作量"
  }}
}}

考虑因素：
1. 业务影响和用户价值
2. 技术复杂度和风险
3. 历史缺陷密度
4. 变更频率
"""
```

## 失败分析Agent Prompt模板

```python
FAILURE_ANALYSIS_PROMPT = """
你是测试分析专家。分析测试失败原因并提供修复建议。

失败信息：
测试用例：{test_case}
错误日志：{error_log}
截图：{screenshot_path}
执行环境：{environment}

输出格式：
{{
  "analysis": {{
    "root_cause": "根本原因",
    "category": "环境问题|代码缺陷|测试脚本问题|数据问题",
    "severity": "critical|high|medium|low",
    "affected_areas": ["影响范围"],
    "reproduction_steps": ["复现步骤"],
    "fix_suggestions": [
      {{
        "target": "修复目标（代码/脚本/环境）",
        "action": "具体操作",
        "priority": "优先级"
      }}
    ],
    "prevention": "预防措施",
    "related_failures": ["相关失败用例ID"]
  }}
}}

分析维度：
1. 错误堆栈分析
2. 页面状态检查
3. 数据一致性验证
4. 环境配置检查
5. 时序问题排查
"""
```

## Prompt工程最佳实践

### 1. 结构化输出
- 始终要求JSON格式输出
- 定义清晰的schema
- 使用示例引导

### 2. 上下文管理
```python
# 使用Few-Shot Learning
EXAMPLES = """
示例1：
输入：用户应该能够登录系统
输出：{{"test_cases": [...]}}

示例2：
输入：系统应在3秒内响应
输出：{{"test_cases": [...]}}
"""
```

### 3. 错误处理
```python
# Prompt中包含验证指令
VALIDATION_INSTRUCTION = """
输出前请自检：
- [ ] 所有必填字段都已填写
- [ ] ID格式正确（REQ_XXX, TC_XXX）
- [ ] 优先级值有效
- [ ] 步骤描述清晰具体
"""
```

### 4. Token优化
- 使用简洁的指令
- 避免重复信息
- 大文档分块处理

### 5. 版本管理
```python
# 每个prompt模板包含版本号
PROMPT_VERSION = "v1.2.0"
PROMPT_CHANGELOG = """
v1.2.0: 增加UI元素识别
v1.1.0: 优化测试数据生成
v1.0.0: 初始版本
"""
```
