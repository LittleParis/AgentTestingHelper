"""
测试主流程 - 使用 fixture 清理测试产物

运行方式:
    # 普通运行
    pytest tests/test_main_flow.py -v

    # 测试前清理
    pytest tests/test_main_flow.py -v --clean-before

    # 测试后保留 output
    pytest tests/test_main_flow.py -v --keep-output
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from main import main as run_main
from utils.llm_client import get_llm_client


class TestMainFlow:
    """主流程测试类"""

    def test_requirement_analysis(self, clean_output):
        """测试需求分析阶段"""
        output_dir = clean_output

        # 运行需求分析
        from parsers.markdown_parser import parse_markdown
        from agents.requirement_analyzer import RequirementAnalyzer

        requirement_file = "examples/requirement_login.md"
        requirement_text = parse_markdown(requirement_file)

        analyzer = RequirementAnalyzer()
        requirements = analyzer.analyze(requirement_text)

        # 验证结果
        assert "requirements" in requirements
        assert len(requirements["requirements"]) > 0

        # 验证文件已保存
        requirements_file = output_dir / "requirements.json"
        assert requirements_file.exists()

        with open(requirements_file, encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data == requirements

    def test_test_case_generation(self, clean_output):
        """测试测试用例生成阶段"""
        output_dir = clean_output

        # 先运行需求分析
        from parsers.markdown_parser import parse_markdown
        from agents.requirement_analyzer import RequirementAnalyzer
        from agents.test_case_generator import TestCaseGenerator

        requirement_file = "examples/requirement_login.md"
        requirement_text = parse_markdown(requirement_file)

        analyzer = RequirementAnalyzer()
        requirements = analyzer.analyze(requirement_text)

        # 生成测试用例
        generator = TestCaseGenerator()
        all_test_cases = []

        for req in requirements["requirements"]:
            test_cases = generator.generate(req)
            all_test_cases.extend(test_cases)

        # 验证结果
        assert len(all_test_cases) > 0

        # 保存并验证
        test_cases_file = output_dir / "test_cases.json"
        with open(test_cases_file, "w", encoding="utf-8") as f:
            json.dump({"test_cases": all_test_cases}, f, ensure_ascii=False, indent=2)

        assert test_cases_file.exists()

    def test_script_generation(self, clean_output, clean_generated_tests):
        """测试脚本生成阶段"""
        output_dir = clean_output
        tests_dir = clean_generated_tests

        # 运行完整流程
        from parsers.markdown_parser import parse_markdown
        from agents.requirement_analyzer import RequirementAnalyzer
        from agents.test_case_generator import TestCaseGenerator
        from automation.midscene_generator import MidsceneScriptGenerator

        requirement_file = "examples/requirement_login.md"
        requirement_text = parse_markdown(requirement_file)

        analyzer = RequirementAnalyzer()
        requirements = analyzer.analyze(requirement_text)

        generator = TestCaseGenerator()
        all_test_cases = []

        for req in requirements["requirements"]:
            test_cases = generator.generate(req)
            all_test_cases.extend(test_cases)

        # 生成测试脚本
        script_gen = MidsceneScriptGenerator(output_dir=str(tests_dir))
        script_file = script_gen.generate(all_test_cases, page_url="https://example.com/login")

        # 验证脚本文件已生成
        generated_files = list(tests_dir.glob("*.spec.ts"))
        assert len(generated_files) > 0

    def test_full_flow(self, clean_all):
        """测试完整流程"""
        output_dir = clean_all["output"]
        tests_dir = clean_all["generated_tests"]

        # 运行主程序
        run_main()

        # 验证 output 文件
        assert (output_dir / "requirements.json").exists()
        assert (output_dir / "test_cases.json").exists()

        # 验证测试脚本
        generated_files = list(tests_dir.glob("*.spec.ts"))
        assert len(generated_files) > 0


class TestLLMClient:
    """LLM 客户端测试"""

    def test_basic_chat(self):
        """测试基本聊天"""
        client = get_llm_client()
        response = client.chat_simple("Hello")
        assert response
        assert len(response) > 0

    def test_message_type(self):
        """测试 Message 类型"""
        from utils.llm_client import Message

        messages = [
            Message.system("You are a test engineer"),
            Message.user("What is unit testing?")
        ]

        client = get_llm_client()
        response = client.chat(messages)
        assert response
        assert "test" in response.lower() or "unit" in response.lower()

    def test_full_response(self):
        """测试完整响应"""
        from utils.llm_client import ChatResponse

        client = get_llm_client()
        response = client.chat_simple("Hi", return_response=True)

        assert isinstance(response, ChatResponse)
        assert response.content
        assert response.total_tokens > 0

    def test_template(self):
        """测试模板聊天"""
        client = get_llm_client()

        response = client.chat_with_template(
            template="Generate {count} test titles for {feature}",
            variables={"feature": "login", "count": 2},
            system_prompt="You are a test expert"
        )
        assert response
