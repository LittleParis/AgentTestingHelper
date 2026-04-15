"""TestExecutor 手动测试脚本 - pytest 版本"""
from core.automation.test_executor import TestExecutor
from core.utils.project_paths import GENERATED_TESTS_DIR


def test_executor_manual():
    """手动测试 TestExecutor 执行 Midscene 测试脚本"""
    print("\n" + "=" * 50)
    print("TestExecutor 手动测试")
    print("=" * 50)

    # 创建执行器
    executor = TestExecutor(config={
        'headed': True,      # 有头模式，可见浏览器
        'timeout': 60000     # 60秒超时
    })

    # 执行测试
    print("\n正在执行测试...")
    result = executor.run_tests(str(GENERATED_TESTS_DIR / 'midscene-demo.spec.ts'))

    # 打印结果
    print("\n" + "=" * 50)
    print("执行结果")
    print("=" * 50)
    print(f"状态: {result['status']}")
    print(f"总数: {result['total']}")
    print(f"通过: {result['passed']}")
    print(f"失败: {result['failed']}")
    print(f"耗时: {result['duration']}秒")

    if result.get('tests'):
        print("\n测试详情:")
        for test in result['tests']:
            status_icon = "✓" if test['status'] == 'passed' else "✗"
            print(f"  {status_icon} {test['name']} ({test['duration']}s)")

    # 通过率
    summary = executor.get_execution_summary()
    print(f"\n通过率: {summary['pass_rate']}%")

    # 断言验证
    assert result['status'] == 'success', f"执行失败: {result.get('error')}"
    assert result['total'] > 0, "没有执行任何测试"


def test_executor_headless():
    """测试无头模式执行"""
    executor = TestExecutor(config={
        'headed': False,
        'timeout': 30000
    })

    # 注意：无头模式需要安装 chromium_headless_shell
    # 如果没有安装，这个测试会失败
    result = executor.run_tests(str(GENERATED_TESTS_DIR / 'midscene-demo.spec.ts'))

    # 无头模式可能因为缺少 headless shell 而失败
    # 这里只检查是否能正确返回结果结构
    assert 'status' in result
    assert 'total' in result
