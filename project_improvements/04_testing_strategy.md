# 测试策略补充

## 🧪 **当前测试现状分析**

### **缺失的测试类型**
```
当前项目测试覆盖情况:
❌ 单元测试 - 完全缺失
❌ 集成测试 - 完全缺失  
❌ 端到端测试 - 完全缺失
❌ 性能测试 - 完全缺失
❌ 错误场景测试 - 完全缺失
```

## 📋 **完整测试策略**

### 1. **单元测试 (Unit Tests)**

#### Agent单元测试
```python
# tests/unit/test_requirement_analyzer.py
import pytest
from unittest.mock import Mock, patch
from agents.requirement_analyzer import RequirementAnalyzer

class TestRequirementAnalyzer:
    
    @pytest.fixture
    def analyzer(self):
        return RequirementAnalyzer()
    
    @pytest.fixture
    def sample_requirement(self):
        return """
        # 用户登录功能
        用户可以通过用户名和密码登录系统
        ## 验收标准
        1. 正确凭证可以登录
        2. 错误凭证显示错误
        """
    
    def test_analyze_success(self, analyzer, sample_requirement):
        """测试正常分析流程"""
        with patch.object(analyzer.llm, 'chat_simple') as mock_llm:
            mock_llm.return_value = '''
            {
                "requirements": [{
                    "id": "REQ_001",
                    "title": "用户登录",
                    "description": "用户登录功能",
                    "priority": "high",
                    "type": "functional",
                    "acceptance_criteria": ["正确凭证可以登录"],
                    "ui_elements": ["用户名输入框", "密码输入框"]
                }],
                "summary": "用户登录功能需求"
            }
            '''
            
            result = analyzer.analyze(sample_requirement)
            
            assert len(result['requirements']) == 1
            assert result['requirements'][0]['id'] == 'REQ_001'
            assert result['requirements'][0]['title'] == '用户登录'
    
    def test_analyze_llm_error(self, analyzer, sample_requirement):
        """测试LLM调用失败场景"""
        with patch.object(analyzer.llm, 'chat_simple') as mock_llm:
            mock_llm.side_effect = Exception("API调用失败")
            
            with pytest.raises(Exception):
                analyzer.analyze(sample_requirement)
    
    def test_analyze_invalid_json(self, analyzer, sample_requirement):
        """测试JSON解析失败场景"""
        with patch.object(analyzer.llm, 'chat_simple') as mock_llm:
            mock_llm.return_value = "无效的JSON格式"
            
            with pytest.raises(json.JSONDecodeError):
                analyzer.analyze(sample_requirement)
    
    def test_build_prompt(self, analyzer):
        """测试Prompt构建"""
        requirement_text = "测试需求"
        prompt = analyzer._build_prompt(requirement_text)
        
        assert "测试需求" in prompt
        assert "JSON" in prompt
        assert "requirements" in prompt

# tests/unit/test_test_case_generator.py
class TestTestCaseGenerator:
    
    @pytest.fixture
    def generator(self):
        return TestCaseGenerator()
    
    @pytest.fixture
    def sample_requirement(self):
        return {
            "id": "REQ_001",
            "title": "用户登录",
            "description": "用户登录功能",
            "acceptance_criteria": ["正确凭证可以登录", "错误凭证显示错误"]
        }
    
    def test_generate_success(self, generator, sample_requirement):
        """测试用例生成成功"""
        with patch.object(generator.llm, 'chat_simple') as mock_llm:
            mock_llm.return_value = '''
            {
                "test_cases": [{
                    "id": "TC_001",
                    "requirement_id": "REQ_001",
                    "title": "正确登录测试",
                    "priority": "high",
                    "type": "functional",
                    "steps": [
                        {"step_number": 1, "action": "输入用户名", "data": "admin", "expected": "输入成功"}
                    ],
                    "expected": "登录成功",
                    "tags": ["smoke"]
                }]
            }
            '''
            
            result = generator.generate(sample_requirement)
            
            assert len(result) == 1
            assert result[0]['id'] == 'TC_001'
            assert result[0]['requirement_id'] == 'REQ_001'
```

#### 工具类单元测试
```python
# tests/unit/test_llm_client.py
class TestLLMClient:
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message.user("测试消息")
        assert msg.role == MessageRole.USER
        assert msg.content == "测试消息"
    
    def test_message_to_dict(self):
        """测试消息转换"""
        msg = Message.system("系统消息")
        result = msg.to_dict()
        assert result == {"role": "system", "content": "系统消息"}
    
    @patch('utils.llm_client.ChatOpenAI')
    def test_llm_client_init(self, mock_openai):
        """测试LLM客户端初始化"""
        client = LLMClient(api_key="test_key", model="test_model")
        assert client.api_key == "test_key"
        assert client.model == "test_model"

# tests/unit/test_markdown_parser.py
class TestMarkdownParser:
    
    def test_parse_markdown_file(self, tmp_path):
        """测试Markdown文件解析"""
        # 创建临时文件
        md_file = tmp_path / "test.md"
        md_file.write_text("# 标题\n内容", encoding="utf-8")
        
        result = parse_markdown(str(md_file))
        assert "# 标题" in result
        assert "内容" in result
    
    def test_extract_sections(self):
        """测试章节提取"""
        content = """
        # 第一章
        第一章内容
        
        # 第二章  
        第二章内容
        """
        
        sections = extract_sections(content)
        assert "第一章" in sections
        assert "第二章" in sections
        assert sections["第一章"].strip() == "第一章内容"
```

### 2. **集成测试 (Integration Tests)**

```python
# tests/integration/test_agent_workflow.py
class TestAgentWorkflow:
    
    @pytest.fixture
    def sample_requirement_file(self, tmp_path):
        """创建测试需求文件"""
        req_file = tmp_path / "test_requirement.md"
        req_file.write_text("""
        # 用户登录功能
        用户可以通过用户名和密码登录系统
        ## 验收标准
        1. 正确凭证可以登录
        2. 错误凭证显示错误
        """, encoding="utf-8")
        return str(req_file)
    
    def test_requirement_to_test_cases_flow(self, sample_requirement_file):
        """测试从需求到测试用例的完整流程"""
        # 1. 解析需求文档
        requirement_text = parse_markdown(sample_requirement_file)
        
        # 2. 分析需求
        analyzer = RequirementAnalyzer()
        requirements = analyzer.analyze(requirement_text)
        
        assert len(requirements['requirements']) > 0
        
        # 3. 生成测试用例
        generator = TestCaseGenerator()
        all_test_cases = []
        
        for req in requirements['requirements']:
            test_cases = generator.generate(req)
            all_test_cases.extend(test_cases)
        
        assert len(all_test_cases) > 0
        
        # 4. 评审测试用例
        reviewer = CaseReviewer()
        review_result = reviewer.review_all(requirements['requirements'], all_test_cases)
        
        assert 'passed' in review_result
        assert 'total_score' in review_result
    
    def test_langgraph_workflow_integration(self, sample_requirement_file):
        """测试LangGraph工作流集成"""
        requirement_text = parse_markdown(sample_requirement_file)
        
        # 运行工作流
        result = run_workflow(
            requirement_text=requirement_text,
            max_iterations=1,
            page_url="https://example.com"
        )
        
        # 验证工作流结果
        assert 'requirements' in result
        assert 'test_cases' in result
        assert 'review_passed' in result
        assert len(result['requirements']) > 0
        assert len(result['test_cases']) > 0

# tests/integration/test_script_generation.py
class TestScriptGeneration:
    
    def test_midscene_script_generation(self):
        """测试Midscene脚本生成"""
        test_cases = [{
            "id": "TC_001",
            "title": "登录测试",
            "steps": [
                {"action": "打开登录页面", "data": "https://example.com/login"},
                {"action": "输入用户名", "data": "admin"},
                {"action": "点击登录按钮", "data": ""}
            ]
        }]
        
        generator = MidsceneScriptGenerator()
        script_path = generator.generate(test_cases, page_url="https://example.com")
        
        # 验证脚本文件存在
        assert Path(script_path).exists()
        
        # 验证脚本内容
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'test(' in content
            assert 'TC_001' in content
            assert 'ai(' in content  # Midscene AI调用
```

### 3. **端到端测试 (E2E Tests)**

```python
# tests/e2e/test_complete_flow.py
class TestCompleteFlow:
    
    @pytest.mark.e2e
    def test_full_automation_pipeline(self, tmp_path):
        """测试完整自动化流程"""
        # 1. 准备测试需求文档
        req_file = tmp_path / "login_requirement.md"
        req_file.write_text("""
        # 用户登录功能需求
        
        ## 功能描述
        用户应该能够使用邮箱和密码登录系统
        
        ## 验收标准
        1. 正确的凭证能够成功登录
        2. 错误的凭证显示相应错误提示
        """, encoding="utf-8")
        
        # 2. 运行完整流程
        from main_v2 import main
        
        # 模拟命令行参数
        import sys
        original_argv = sys.argv
        sys.argv = ['main_v2.py']
        
        try:
            # 临时修改需求文件路径
            import agents.workflow
            original_file = "examples/requirement_baidu.md"
            agents.workflow.requirement_file = str(req_file)
            
            # 执行主流程
            main()
            
            # 验证输出文件
            output_files = list(Path("output").glob("*.json"))
            assert len(output_files) > 0
            
            # 验证生成的脚本
            script_files = list(Path("midscene_run/generated").glob("*.spec.ts"))
            assert len(script_files) > 0
            
        finally:
            sys.argv = original_argv
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_with_real_llm(self):
        """使用真实LLM的端到端测试"""
        # 需要真实的API密钥
        if not os.getenv("LLM_KEY"):
            pytest.skip("需要LLM_KEY环境变量")
        
        requirement_text = """
        # 简单计算器功能
        用户可以进行基本的数学运算
        ## 验收标准
        1. 支持加减乘除运算
        2. 显示计算结果
        """
        
        result = run_workflow(
            requirement_text=requirement_text,
            max_iterations=1,
            page_url="https://calculator.example.com"
        )
        
        # 验证真实LLM的输出质量
        assert len(result['requirements']) > 0
        assert len(result['test_cases']) > 0
        assert result['review_score'] > 0
```

### 4. **性能测试**

```python
# tests/performance/test_performance.py
import time
import pytest
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    
    def test_llm_call_performance(self):
        """测试LLM调用性能"""
        client = get_llm_client()
        
        start_time = time.time()
        response = client.chat_simple("1+1等于几?")
        end_time = time.time()
        
        # LLM调用应该在30秒内完成
        assert end_time - start_time < 30
        assert response is not None
    
    def test_concurrent_agent_execution(self):
        """测试并发Agent执行"""
        def run_analyzer():
            analyzer = RequirementAnalyzer()
            return analyzer.analyze("简单需求测试")
        
        # 并发执行多个分析任务
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_analyzer) for _ in range(3)]
            results = [f.result() for f in futures]
        
        # 所有任务都应该成功完成
        assert len(results) == 3
        for result in results:
            assert 'requirements' in result
    
    def test_large_requirement_processing(self):
        """测试大型需求文档处理"""
        # 生成大型需求文档
        large_requirement = "# 大型系统需求\n" + "\n".join([
            f"## 功能{i}\n功能{i}的详细描述" * 100
            for i in range(10)
        ])
        
        start_time = time.time()
        analyzer = RequirementAnalyzer()
        result = analyzer.analyze(large_requirement)
        end_time = time.time()
        
        # 大型文档处理应该在合理时间内完成
        assert end_time - start_time < 120  # 2分钟
        assert len(result['requirements']) > 0
```

### 5. **错误场景测试**

```python
# tests/error_scenarios/test_error_handling.py
class TestErrorHandling:
    
    def test_network_timeout(self):
        """测试网络超时处理"""
        with patch('utils.llm_client.ChatOpenAI') as mock_openai:
            mock_openai.side_effect = TimeoutError("网络超时")
            
            analyzer = RequirementAnalyzer()
            
            # 应该有适当的错误处理
            with pytest.raises((TimeoutError, LLMError)):
                analyzer.analyze("测试需求")
    
    def test_api_rate_limit(self):
        """测试API限流处理"""
        with patch('utils.llm_client.ChatOpenAI') as mock_openai:
            mock_openai.side_effect = Exception("Rate limit exceeded")
            
            analyzer = RequirementAnalyzer()
            
            # 应该有重试机制
            with pytest.raises(Exception):
                analyzer.analyze("测试需求")
    
    def test_invalid_requirement_format(self):
        """测试无效需求格式处理"""
        analyzer = RequirementAnalyzer()
        
        # 空需求
        result = analyzer.analyze("")
        assert 'error' in result or len(result.get('requirements', [])) == 0
        
        # 乱码需求
        result = analyzer.analyze("乱码内容@#$%^&*()")
        assert isinstance(result, dict)
    
    def test_disk_space_full(self, tmp_path):
        """测试磁盘空间不足处理"""
        # 模拟磁盘空间不足
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = OSError("No space left on device")
            
            generator = MidsceneScriptGenerator(output_dir=str(tmp_path))
            
            with pytest.raises(OSError):
                generator.generate([{"id": "TC_001", "title": "测试"}])

# 测试配置
# pytest.ini
[tool:pytest]
markers =
    e2e: 端到端测试
    slow: 慢速测试
    integration: 集成测试
    unit: 单元测试
    performance: 性能测试
```

### 6. **测试数据管理**

```python
# tests/fixtures/test_data.py
@pytest.fixture
def sample_requirements():
    """标准测试需求数据"""
    return {
        "simple_login": """
        # 用户登录
        用户通过用户名密码登录
        ## 验收标准
        1. 正确凭证登录成功
        2. 错误凭证显示错误
        """,
        "complex_ecommerce": """
        # 电商购物流程
        用户可以浏览商品、加入购物车、下单支付
        ## 验收标准
        1. 商品浏览正常
        2. 购物车功能正常
        3. 支付流程完整
        """,
        "invalid_format": "这不是一个有效的需求文档格式"
    }

@pytest.fixture
def sample_test_cases():
    """标准测试用例数据"""
    return [
        {
            "id": "TC_001",
            "requirement_id": "REQ_001",
            "title": "正确登录测试",
            "priority": "high",
            "type": "functional",
            "steps": [
                {"step_number": 1, "action": "打开登录页面", "data": "", "expected": "页面加载成功"},
                {"step_number": 2, "action": "输入用户名", "data": "admin", "expected": "输入成功"},
                {"step_number": 3, "action": "输入密码", "data": "password", "expected": "输入成功"},
                {"step_number": 4, "action": "点击登录按钮", "data": "", "expected": "登录成功"}
            ],
            "expected": "用户成功登录系统",
            "tags": ["smoke", "positive"]
        }
    ]
```

这个完整的测试策略确保了项目的质量和稳定性，覆盖了从单元测试到端到端测试的各个层面。