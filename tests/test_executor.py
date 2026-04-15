"""TestExecutor 单元测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.test_executor import TestExecutor
from utils.project_paths import GENERATED_TESTS_DIR


class TestTestExecutor:
    """TestExecutor 测试类"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        executor = TestExecutor()
        assert executor.config is not None
        assert executor.config["browser"] == "chromium"
        assert executor.config["timeout"] == 120000
        assert executor.config["headed"] is False

    def test_init_custom_config(self):
        """测试自定义配置"""
        executor = TestExecutor(config={
            "headed": True,
            "timeout": 30000
        })
        assert executor.config["headed"] is True
        assert executor.config["timeout"] == 30000
        # 其他配置保持默认
        assert executor.config["browser"] == "chromium"

    def test_build_command_basic(self):
        """测试基本命令构建"""
        executor = TestExecutor()
        cmd = executor._build_playwright_command("test.spec.ts")

        assert "npx" in cmd
        assert "playwright" in cmd
        assert "test" in cmd
        assert "test.spec.ts" in cmd

    def test_build_command_args_basic(self):
        """测试 subprocess 参数列表构建"""
        executor = TestExecutor()
        args = executor._build_playwright_command_args("test.spec.ts")

        assert args[1:4] == ["playwright", "test", "test.spec.ts"]
        assert any(arg.startswith("--timeout=") for arg in args)

    def test_build_command_headed(self):
        """测试有头模式命令"""
        executor = TestExecutor(config={"headed": True})
        cmd = executor._build_playwright_command("test.spec.ts")

        assert "--headed" in cmd

    def test_build_command_grep(self):
        """测试 grep 过滤"""
        executor = TestExecutor(config={"grep": "login"})
        cmd = executor._build_playwright_command("test.spec.ts")

        assert "--grep" in cmd
        assert "login" in cmd

    def test_build_command_project(self):
        """测试项目配置"""
        executor = TestExecutor(config={"project": "chromium"})
        cmd = executor._build_playwright_command("test.spec.ts")

        assert "--project" in cmd
        assert "chromium" in cmd

    def test_parse_output_passed(self):
        """测试解析通过的测试"""
        executor = TestExecutor()
        output = """
Running 2 tests using 1 worker

  ✓  [chromium] › login.spec.ts:10:3 › TC_001: 用户登录 (3.5s)
  ✓  [chromium] › login.spec.ts:25:3 › TC_002: 密码错误 (2.1s)

  2 passed (5.6s)
"""
        result = executor.parse_playwright_output(output)

        assert result["passed"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2
        assert len(result["tests"]) == 2

    def test_parse_output_failed(self):
        """测试解析失败的测试"""
        executor = TestExecutor()
        output = """
Running 2 tests using 1 worker

  ✓  [chromium] › login.spec.ts:10:3 › TC_001: 用户登录 (3.5s)
  ✘  [chromium] › login.spec.ts:25:3 › TC_002: 密码错误 (5.2s)

  1 failed
  1 passed (8.7s)
"""
        result = executor.parse_playwright_output(output)

        assert result["passed"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2

    def test_parse_output_failed_with_cross_marker(self):
        """测试解析使用 ✘ 标记的失败测试"""
        executor = TestExecutor()
        output = """
Running 1 test using 1 worker

  ✘  [chromium] › login.spec.ts:25:3 › TC_002: 密码错误 (5.2s)

  1 failed
"""
        result = executor.parse_playwright_output(output)

        assert result["failed"] == 1
        assert result["total"] == 1

    def test_parse_output_with_x_marker(self):
        """测试解析使用 x 标记的失败测试"""
        executor = TestExecutor()
        output = """
Running 2 tests using 2 workers

  x  1 [chromium] › test.spec.ts:10:3 › Test A (30.1s)
  x  2 [chromium] › test.spec.ts:20:3 › Test B (25.0s)

  2 failed (55.1s)
"""
        result = executor.parse_playwright_output(output)

        assert result["failed"] == 2
        assert result["total"] == 2

    def test_parse_output_mixed(self):
        """测试解析混合结果"""
        executor = TestExecutor()
        output = """
Running 3 tests using 1 worker

  ✓  [chromium] › test.spec.ts:10:3 › Test A (1.0s)
  ✘  [chromium] › test.spec.ts:20:3 › Test B (2.0s)
  -  [chromium] › test.spec.ts:30:3 › Test C

  1 failed
  1 passed
  1 skipped
"""
        result = executor.parse_playwright_output(output)

        assert result["passed"] == 1
        assert result["failed"] == 1
        assert result["skipped"] == 1
        assert result["total"] == 3

    def test_parse_output_empty(self):
        """测试解析空输出"""
        executor = TestExecutor()
        result = executor.parse_playwright_output("")

        assert result["total"] == 0
        assert result["passed"] == 0
        assert result["failed"] == 0

    def test_run_tests_file_not_found(self):
        """测试文件不存在的情况"""
        executor = TestExecutor()
        result = executor.run_tests("nonexistent.spec.ts")

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_get_execution_summary_no_results(self):
        """测试无结果时的摘要"""
        executor = TestExecutor()
        summary = executor.get_execution_summary()

        assert summary["status"] == "no_results"

    def test_get_failed_tests_empty(self):
        """测试获取失败测试（空）"""
        executor = TestExecutor()
        failed = executor.get_failed_tests()

        assert failed == []

    def test_calculate_pass_rate(self):
        """测试通过率计算"""
        executor = TestExecutor()
        executor._last_results = {
            "total": 10,
            "passed": 8,
            "failed": 2
        }

        rate = executor._calculate_pass_rate()
        assert rate == 80.0

    def test_determine_execution_status(self):
        """测试执行状态判断"""
        executor = TestExecutor()

        assert executor._determine_execution_status(0, {"failed": 0, "total": 1}) == "success"
        assert executor._determine_execution_status(1, {"failed": 1, "total": 1}) == "failed"
        assert executor._determine_execution_status(1, {"failed": 0, "total": 0}) == "error"


class TestTestExecutorIntegration:
    """集成测试 - 需要实际测试脚本"""

    def test_run_existing_script(self):
        """测试执行已存在的脚本"""
        # 检查是否有生成的测试脚本
        test_dir = GENERATED_TESTS_DIR
        spec_files = list(test_dir.glob("*.spec.ts")) if test_dir.exists() else []

        if not spec_files:
            # 跳过测试
            return

        executor = TestExecutor(config={
            "headed": False,
            "timeout": 30000
        })

        result = executor.run_tests(str(spec_files[0]))

        # 验证结果结构
        assert "status" in result
        assert "total" in result
        assert "passed" in result
        assert "failed" in result
        assert "duration" in result

    def test_run_with_browsers_path(self):
        """测试使用自定义浏览器路径"""
        browsers_path = Path("browsers")
        if not browsers_path.exists():
            return

        executor = TestExecutor(config={
            "browsers_path": str(browsers_path.absolute()),
            "headed": False,
            "timeout": 30000
        })

        # 验证配置
        assert executor.config["browsers_path"] is not None
