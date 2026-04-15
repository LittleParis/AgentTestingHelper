# 实践项目 - 动手练习

## 练习1: 创建自己的需求文档

### 任务: 编写一个简单的需求文档
```markdown
# 文件: examples/my_requirement.md

# 用户注册功能需求

## 功能描述
新用户可以通过填写表单注册账号

## 详细需求
- 用户名输入框 (必填，3-20字符)
- 邮箱输入框 (必填，有效邮箱格式)
- 密码输入框 (必填，至少6位)
- 确认密码输入框 (必填，与密码一致)
- 注册按钮

## 验收标准
1. 所有字段验证正确时可以成功注册
2. 用户名重复时显示"用户名已存在"
3. 邮箱格式错误时显示"请输入有效邮箱"
4. 密码不一致时显示"两次密码不一致"
```

### 练习步骤:
```python
# 1. 运行需求分析
from parsers.markdown_parser import parse_markdown
from agents.requirement_analyzer import RequirementAnalyzer

content = parse_markdown("examples/my_requirement.md")
analyzer = RequirementAnalyzer()
requirements = analyzer.analyze(content)

# 2. 生成测试用例
from agents.test_case_generator import TestCaseGenerator

generator = TestCaseGenerator()
all_test_cases = []
for req in requirements['requirements']:
    test_cases = generator.generate(req)
    all_test_cases.extend(test_cases)

# 3. 评审测试用例
from agents.case_reviewer import CaseReviewer

reviewer = CaseReviewer()
review_result = reviewer.review_all(requirements['requirements'], all_test_cases)

print(f"评审结果: {review_result['passed']}")
print(f"总分: {review_result['total_score']}")
```

## 练习2: 修改Agent行为

### 任务: 自定义测试用例生成的Prompt
```python
# 修改 agents/test_case_generator.py 中的 _build_prompt 方法
# 添加更多测试类型，如性能测试、安全测试等

def _build_prompt(self, requirement: Dict[str, Any]) -> str:
    req_json = json.dumps(requirement, ensure_ascii=False, indent=2)
    
    return f"""
你是一个资深测试工程师。基于以下需求，生成全面的测试用例。

需求信息：
{req_json}

测试用例类型要求:
1. 功能测试 (正向场景)
2. 异常测试 (负向场景) 
3. 边界值测试
4. 用户体验测试
5. 兼容性测试 (可选)

输出格式（JSON）：
... (保持原有格式)
"""
```

## 练习3: 添加新的Agent

### 任务: 创建一个"测试数据生成Agent"
```python
# 文件: agents/test_data_generator.py

class TestDataGenerator:
    """测试数据生成Agent"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    def generate_test_data(self, test_cases: List[Dict]) -> Dict:
        """为测试用例生成测试数据"""
        prompt = self._build_prompt(test_cases)
        response = self.llm.chat_simple(prompt)
        return self._parse_response(response)
    
    def _build_prompt(self, test_cases: List[Dict]) -> str:
        return f"""
基于以下测试用例，生成对应的测试数据：

测试用例: {json.dumps(test_cases, ensure_ascii=False, indent=2)}

请生成:
1. 有效测试数据 (正向测试用)
2. 无效测试数据 (负向测试用)
3. 边界值数据
4. 特殊字符数据

输出JSON格式...
"""
```

## 练习4: 集成到工作流

### 任务: 将新Agent添加到LangGraph工作流
```python
# 修改 agents/workflow.py

def generate_test_data_node(state: AgentState) -> dict:
    """测试数据生成节点"""
    print("\n[Agent] 生成测试数据...")
    
    test_cases = state.get("test_cases", [])
    generator = TestDataGenerator()
    test_data = generator.generate_test_data(test_cases)
    
    return {
        "test_data": test_data,
        "current_step": "test_data_generated"
    }

# 在 build_workflow() 中添加节点和边
workflow.add_node("generate_test_data", generate_test_data_node)
workflow.add_edge("review_test_cases", "generate_test_data")
workflow.add_edge("generate_test_data", "generate_script")
```

## 练习5: 完整项目运行

### 任务: 运行完整流程并分析结果
```python
# 运行完整的main_v2.py
python main_v2.py

# 分析输出文件
import json

# 1. 查看需求分析结果
with open("output/requirements_xxx.json", "r", encoding="utf-8") as f:
    requirements = json.load(f)
    print("需求分析结果:", requirements)

# 2. 查看测试用例
with open("output/test_cases_xxx.json", "r", encoding="utf-8") as f:
    test_cases = json.load(f)
    print(f"生成了 {len(test_cases['test_cases'])} 个测试用例")

# 3. 查看评审结果
with open("output/review_xxx.json", "r", encoding="utf-8") as f:
    review = json.load(f)
    print(f"评审得分: {review['score']}")

# 4. 查看生成的测试脚本
script_files = list(Path("midscene_run/generated").glob("*.spec.ts"))
if script_files:
    with open(script_files[0], "r", encoding="utf-8") as f:
        print("生成的脚本预览:")
        print(f.read()[:500] + "...")
```