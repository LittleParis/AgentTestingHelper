"""
Agent 工作流 - 基于 LangGraph 的多 Agent 协作

阶段2核心功能：
- 状态管理：多个 Agent 共享状态
- 协作流程：需求分析 → 用例生成 → 用例评审

阶段3扩展：
- 脚本生成：测试用例 → Midscene 脚本
- 测试执行：执行脚本并收集结果
- 报告生成：Allure 测试报告
"""
import os

# 清除代理设置（解决连接问题）
for _var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(_var, None)
os.environ['NO_PROXY'] = '*'

from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from agents.requirement_analyzer import RequirementAnalyzer
from agents.test_case_generator import TestCaseGenerator
from agents.case_reviewer import CaseReviewer
from automation.midscene_generator import MidsceneScriptGenerator
from automation.test_executor import TestExecutor
from automation.allure_reporter import AllureReporter
from utils.project_paths import GENERATED_TESTS_DIR


# ============ 状态定义 ============

class AgentState(TypedDict):
    """Agent 共享状态

    所有 Agent 都可以读取和修改这个状态
    """
    # 输入
    requirement_text: str                    # 原始需求文档文本

    # 需求分析结果
    requirements: Optional[List[dict]]       # 结构化需求列表
    requirement_summary: Optional[str]       # 需求摘要

    # 测试用例
    test_cases: Optional[List[dict]]         # 生成的测试用例

    # 评审结果
    review_passed: Optional[bool]            # 评审是否通过
    review_score: Optional[float]            # 评审分数 (0-100)
    review_comments: Optional[List[dict]]    # 评审意见
    review_suggestions: Optional[List[str]]  # 改进建议

    # 反馈与迭代
    iteration_count: int                     # 迭代次数
    max_iterations: int                      # 最大迭代次数
    feedback: Optional[List[str]]            # 反馈信息

    # 阶段3新增：脚本生成与执行
    generated_script: Optional[str]          # 生成的测试脚本路径
    page_url: Optional[str]                  # 目标页面 URL
    execution_results: Optional[dict]        # 测试执行结果
    allure_report_path: Optional[str]        # Allure 报告路径

    # 执行状态
    current_step: str                        # 当前步骤
    agent_messages: List[dict]               # Agent 间消息（自定义格式）


# ============ Agent 节点函数 ============

def analyze_requirements_node(state: AgentState) -> dict:
    """
    需求分析节点

    输入：requirement_text
    输出：requirements, requirement_summary
    """
    print("\n[Agent] 需求分析中...")

    analyzer = RequirementAnalyzer()
    result = analyzer.analyze(state["requirement_text"])

    return {
        "requirements": result.get("requirements", []),
        "requirement_summary": result.get("summary", ""),
        "current_step": "requirement_analyzed",
        "agent_messages": [{"role": "analyzer", "content": f"识别到 {len(result.get('requirements', []))} 个需求"}]
    }


def generate_test_cases_node(state: AgentState) -> dict:
    """
    测试用例生成节点

    输入：requirements
    输出：test_cases
    """
    print("\n[Agent] 生成测试用例...")

    generator = TestCaseGenerator()
    all_test_cases = []

    requirements = state.get("requirements", [])
    for req in requirements:
        try:
            test_cases = generator.generate(req)
            all_test_cases.extend(test_cases)
            print(f"  [OK] {req['id']}: 生成 {len(test_cases)} 个用例")
        except Exception as e:
            print(f"  [FAIL] {req['id']}: {e}")

    return {
        "test_cases": all_test_cases,
        "current_step": "test_cases_generated",
        "agent_messages": [{"role": "generator", "content": f"共生成 {len(all_test_cases)} 个测试用例"}]
    }


def review_test_cases_node(state: AgentState) -> dict:
    """
    测试用例评审节点（使用 LLM 智能评审）

    输入：requirements, test_cases
    输出：review_passed, review_score, review_comments, review_suggestions
    """
    print("\n[Agent] 评审测试用例（LLM 智能评审）...")

    requirements = state.get("requirements", [])
    test_cases = state.get("test_cases", [])

    try:
        reviewer = CaseReviewer()
        result = reviewer.review_all(requirements, test_cases)

        passed = result.get("passed", False)
        score = result.get("total_score", 0)
        details = result.get("details", [])
        summary = result.get("summary", "")

        # 汇总所有评审意见
        all_comments = []
        all_suggestions = []

        for detail in details:
            req_id = detail.get("requirement_id", "")
            for comment in detail.get("comments", []):
                comment["requirement_id"] = req_id
                all_comments.append(comment)

            # 收集改进建议
            for suggestion in detail.get("suggestions", []):
                all_suggestions.append(f"[{req_id}] {suggestion}")

        if passed:
            print(f"  [OK] 评审通过，得分: {score}")
        else:
            print(f"  [WARN] 评审未通过，得分: {score}")
            print(f"  发现 {len(all_comments)} 个问题")

        return {
            "review_passed": passed,
            "review_score": score,
            "review_comments": all_comments,
            "review_suggestions": all_suggestions,
            "current_step": "reviewed",
            "agent_messages": [{
                "role": "reviewer",
                "content": f"评审{'通过' if passed else '未通过'}，得分: {score}/100"
            }]
        }

    except Exception as e:
        print(f"  [ERROR] LLM 评审失败: {e}")
        # 降级到简单规则评审
        return _simple_review(requirements, test_cases)


# ============ 路由函数 ============

def should_regenerate(state: AgentState) -> str:
    """
    决定是否需要重新生成测试用例

    Returns:
        "regenerate": 返回用例生成节点
        "end": 结束流程
    """
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 2)

    # 超过最大迭代次数，强制结束
    if iteration >= max_iterations:
        print(f"\n[Workflow] 达到最大迭代次数 {max_iterations}，结束流程")
        return "end"

    # 评审通过，结束
    if state.get("review_passed", False):
        return "end"

    # 评审未通过，需要重新生成
    return "regenerate"


def increment_iteration(state: AgentState) -> dict:
    """增加迭代计数"""
    return {"iteration_count": state.get("iteration_count", 0) + 1}

def _simple_review(requirements: List[dict], test_cases: List[dict]) -> dict:
    """
    简单规则评审（降级方案）
    """
    print("  [INFO] 使用简单规则评审...")

    comments = []
    passed = True
    score = 100

    # 检查1：每个需求是否有对应的测试用例
    req_ids = {req["id"] for req in requirements}
    tc_req_ids = set()
    for tc in test_cases:
        tc_id = tc.get("id", "")
        if tc_id.startswith("TC_"):
            req_num = tc_id.split("_")[1]
            tc_req_ids.add(f"REQ_{req_num}")

    missing_reqs = req_ids - tc_req_ids
    if missing_reqs:
        passed = False
        score -= 20
        comments.append({
            "type": "missing_coverage",
            "severity": "high",
            "message": f"以下需求缺少测试用例: {missing_reqs}"
        })

    # 检查2：测试用例是否有预期结果
    for tc in test_cases:
        if not tc.get("expected"):
            score -= 5
            comments.append({
                "type": "missing_expected",
                "severity": "medium",
                "message": f"{tc['id']} 缺少预期结果"
            })

    # 检查3：测试用例数量合理性
    if len(test_cases) < len(requirements):
        passed = False
        score -= 20
        comments.append({
            "type": "insufficient_cases",
            "severity": "high",
            "message": f"测试用例数量({len(test_cases)})少于需求数量({len(requirements)})"
        })

    return {
        "review_passed": passed,
        "review_score": max(score, 0),
        "review_comments": comments,
        "review_suggestions": [],
        "current_step": "reviewed",
        "agent_messages": [{
            "role": "reviewer",
            "content": f"评审{'通过' if passed else '未通过'}，得分: {max(score, 0)}/100"
        }]
    }


def optimize_test_cases_node(state: AgentState) -> dict:
    """优化测试用例"""
    test_cases = state["test_cases"]

    # 优化逻辑
    optimized = []
    for tc in test_cases:
        # 添加缺失的字段
        if "priority" not in tc:
            tc["priority"] = "medium"
        optimized.append(tc)

    return {"test_cases": optimized}


# ============ 阶段3新增节点 ============

def generate_script_node(state: AgentState) -> dict:
    """
    脚本生成节点

    输入：test_cases, page_url
    输出：generated_script
    """
    print("\n[Agent] 生成 Midscene 测试脚本...")

    test_cases = state.get("test_cases", [])
    page_url = state.get("page_url", "https://example.com")

    if not test_cases:
        print("  [WARN] 没有测试用例，跳过脚本生成")
        return {
            "generated_script": None,
            "current_step": "script_skipped"
        }

    # 生成脚本
    generator = MidsceneScriptGenerator(output_dir=str(GENERATED_TESTS_DIR))
    script_path = generator.generate(test_cases, page_url=page_url)

    # 验证脚本是否真的存在
    import os
    abs_path = os.path.abspath(script_path)
    exists = os.path.exists(abs_path)
    print(f"  [DEBUG] 生成的脚本路径: {script_path}")
    print(f"  [DEBUG] 绝对路径: {abs_path}")
    print(f"  [DEBUG] 文件存在: {exists}")

    if not exists:
        print(f"  [ERROR] 脚本文件不存在!")
        return {
            "generated_script": None,
            "current_step": "script_failed"
        }

    print(f"  [OK] 脚本已生成: {script_path}")

    return {
        "generated_script": script_path,
        "current_step": "script_generated",
        "agent_messages": [{"role": "generator", "content": f"生成测试脚本: {script_path}"}]
    }


def execute_tests_node(state: AgentState) -> dict:
    """
    测试执行节点

    输入：generated_script
    输出：execution_results
    """
    print("\n[Agent] 执行测试脚本...")

    script_path = state.get("generated_script")

    if not script_path:
        print("  [WARN] 没有测试脚本，跳过执行")
        return {
            "execution_results": None,
            "current_step": "execution_skipped"
        }

    # 调试：检查脚本是否存在
    import os
    abs_path = os.path.abspath(script_path)
    print(f"  [DEBUG] 脚本路径: {script_path}")
    print(f"  [DEBUG] 绝对路径: {abs_path}")
    print(f"  [DEBUG] 文件存在: {os.path.exists(abs_path)}")

    # 执行测试
    executor = TestExecutor(config={
        "headed": True,      # 有头模式，方便调试
        "timeout": 180000,   # 180秒超时（Midscene AI 需要更长时间）
    })

    result = executor.run_tests(script_path)

    # 如果运行环境在真正执行前就失败，按测试用例数写入兜底 Allure 失败结果，
    # 保证全流程仍能产生失败统计和报告。
    if result.get("status") == "error" and result.get("total", 0) == 0:
        reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")
        fallback = reporter.write_fallback_results(
            test_cases=state.get("test_cases", []) or [],
            error_message=result.get("error") or result.get("stderr") or result.get("raw_output") or "测试执行失败",
            script_path=script_path,
        )
        if fallback["created"] > 0:
            result.update({
                "status": "failed",
                "total": fallback["total"],
                "passed": fallback["passed"],
                "failed": fallback["failed"],
                "skipped": fallback["skipped"],
            })
            print(f"  [WARN] 执行器未产出测试结果，已写入 {fallback['created']} 条兜底失败结果")

    # 打印结果摘要
    print(f"  [OK] 执行完成")
    print(f"       总数: {result['total']}")
    print(f"       通过: {result['passed']}")
    print(f"       失败: {result['failed']}")
    print(f"       耗时: {result['duration']}秒")

    return {
        "execution_results": result,
        "current_step": "tests_executed",
        "agent_messages": [{
            "role": "executor",
            "content": f"执行完成: {result['passed']}/{result['total']} 通过"
        }]
    }


def generate_report_node(state: AgentState) -> dict:
    """
    报告生成节点

    输入：execution_results
    输出：allure_report_path
    """
    print("\n[Agent] 生成 Allure 测试报告...")

    reporter = AllureReporter(results_dir="allure-results", report_dir="allure-report")

    # 检查 Allure 是否安装
    if not reporter.check_allure_installed():
        print("  [WARN] Allure 未安装，跳过报告生成")
        print("  安装命令: npm install -g allure-commandline")
        return {
            "allure_report_path": None,
            "current_step": "report_skipped"
        }

    # 生成报告
    result = reporter.generate_report()

    if result["status"] == "success":
        print(f"  [OK] 报告已生成: {result['report_path']}")
        return {
            "allure_report_path": result["report_path"],
            "current_step": "report_generated",
            "agent_messages": [{
                "role": "reporter",
                "content": f"Allure 报告已生成"
            }]
        }
    else:
        print(f"  [WARN] 报告生成失败: {result['error']}")
        return {
            "allure_report_path": None,
            "current_step": "report_failed"
        }


# ============ 构建工作流图 ============

def build_workflow() -> StateGraph:
    """
    构建 Agent 协作工作流

    阶段2流程:
        START → analyze_requirements → generate_test_cases → review_test_cases
                                                                      ↓
                                                              should_regenerate?
                                                              ↙        ↘
                                                    regenerate         END
                                                        ↓
                                                generate_test_cases

    阶段3扩展:
        ... → review_test_cases (通过) → generate_script → execute_tests → generate_report → END
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("analyze_requirements", analyze_requirements_node)
    workflow.add_node("generate_test_cases", generate_test_cases_node)
    workflow.add_node("review_test_cases", review_test_cases_node)
    workflow.add_node("increment_iteration", increment_iteration)
    # 阶段3新增节点
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("execute_tests", execute_tests_node)
    workflow.add_node("generate_report", generate_report_node)

    # 设置入口
    workflow.set_entry_point("analyze_requirements")

    # 添加边
    workflow.add_edge("analyze_requirements", "generate_test_cases")
    workflow.add_edge("generate_test_cases", "review_test_cases")

    # 条件边：评审后决定下一步
    # 通过 → 生成脚本 → 执行测试 → 生成报告 → END
    # 不通过 → 迭代重新生成
    workflow.add_conditional_edges(
        "review_test_cases",
        should_regenerate,
        {
            "regenerate": "increment_iteration",
            "end": "generate_script"  # 评审通过，进入脚本生成
        }
    )

    # 迭代后重新生成
    workflow.add_edge("increment_iteration", "generate_test_cases")

    # 阶段3新增边：脚本生成 → 测试执行 → 报告生成 → END
    workflow.add_edge("generate_script", "execute_tests")
    workflow.add_edge("execute_tests", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow


def run_workflow(requirement_text: str, max_iterations: int = 2, page_url: str = "https://example.com") -> AgentState:
    """
    运行 Agent 协作工作流

    Args:
        requirement_text: 需求文档文本
        max_iterations: 最大迭代次数
        page_url: 目标页面 URL（阶段3新增）

    Returns:
        最终状态
    """
    # 初始状态
    initial_state: AgentState = {
        "requirement_text": requirement_text,
        "requirements": None,
        "requirement_summary": None,
        "test_cases": None,
        "review_passed": None,
        "review_score": None,
        "review_comments": None,
        "review_suggestions": None,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "feedback": [],
        # 阶段3新增
        "generated_script": None,
        "page_url": page_url,
        "execution_results": None,
        "allure_report_path": None,
        "current_step": "init",
        "agent_messages": []
    }

    # 构建并编译工作流
    workflow = build_workflow()
    app = workflow.compile()

    # 运行
    print("=" * 60)
    print("Agent 协作工作流启动")
    print("=" * 60)

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("Agent 协作工作流完成")
    print("=" * 60)

    return final_state


# ============ 测试 ============

if __name__ == "__main__":
    # 测试工作流
    test_requirement = """
    # 用户登录功能

    ## 功能描述
    用户可以通过用户名和密码登录系统。

    ## 验收标准
    1. 正确的用户名和密码可以成功登录
    2. 错误的密码提示"密码错误"
    3. 用户名不存在提示"用户不存在"
    4. 密码输入3次错误后锁定账户
    """

    result = run_workflow(test_requirement, page_url="https://example.com/login")

    print("\n最终结果:")
    print(f"- 需求数量: {len(result.get('requirements', []))}")
    print(f"- 用例数量: {len(result.get('test_cases', []))}")
    print(f"- 评审通过: {result.get('review_passed')}")
    print(f"- 迭代次数: {result.get('iteration_count')}")

    # 阶段3新增输出
    print(f"- 生成脚本: {result.get('generated_script')}")
    exec_results = result.get('execution_results')
    if exec_results:
        print(f"- 执行结果: {exec_results['passed']}/{exec_results['total']} 通过")
        print(f"- 执行耗时: {exec_results['duration']}秒")
