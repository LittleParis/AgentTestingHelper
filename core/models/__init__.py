"""
数据模型模块

使用 Pydantic 定义项目中的核心数据结构，提供：
- 类型安全
- 数据验证
- 自动序列化/反序列化
- JSON Schema 生成
"""

from .workflow import (
    AgentState,
    SingleRequirementGenerationState,
    ScenarioConfig,
    merge_lists,
)

from .requirement import (
    Requirement,
    RequirementType,
    Priority,
    RequirementAnalysisResult
)

from .test_case import (
    TestCase,
    TestCaseType,
    TestStep,
    TestCaseGenerationResult
)

from .test_strategy import (
    CoverageAxis,
    ExecutionMode,
    FocusLevel,
    FocusPointStrategy,
    OverallRisk,
    RequirementStrategy,
    TestStrategyPlan,
)

from .script_plan import (
    AssertionIntent,
    AssertionKind,
    ExecutionPolicy,
    ExecutionTarget,
    FallbackPolicy,
    IntentType,
    NativeOperation,
    NativeOperationKind,
    PlannerDecisionTrace,
    ScenarioPlan,
    ScriptExecutionPlan,
    ScriptSetupPlan,
    ScriptStepPlan,
)

from .review import (
    ReviewResult,
    ReviewAllResult,
    ReviewDimensions,
    ReviewComment,
    RequirementReviewDetail,
    CommentType,
    CommentSeverity
)

from .runtime import (
    BenchmarkCase,
    ExecutionFailureCategory,
    FailureAnalysisResult,
    RunManifest,
)

from .config import (
    LLMConfig,
    TestConfig,
    AllureConfig,
    LogConfig,
    WorkflowConfig,
    ProjectSettings,
    get_settings
)

# 从 llm_client 导出（避免循环导入，这里只是重新导出）
try:
    from core.utils.llm_client import (
        Message,
        MessageRole,
        ChatResponse,
        TokenUsage,
        FinishReason
    )
except Exception:  # pragma: no cover - optional dependency may be unavailable in lightweight test envs
    Message = None
    MessageRole = None
    ChatResponse = None
    TokenUsage = None
    FinishReason = None

__all__ = [
    # 工作流模型
    "AgentState",
    "SingleRequirementGenerationState",
    "ScenarioConfig",
    "merge_lists",

    # 需求模型
    "Requirement",
    "RequirementType",
    "Priority",
    "RequirementAnalysisResult",

    # 测试用例模型
    "TestCase",
    "TestCaseType",
    "TestStep",
    "TestCaseGenerationResult",
    "CoverageAxis",
    "ExecutionMode",
    "FocusLevel",
    "FocusPointStrategy",
    "OverallRisk",
    "RequirementStrategy",
    "TestStrategyPlan",
    "AssertionIntent",
    "AssertionKind",
    "ExecutionPolicy",
    "ExecutionTarget",
    "FallbackPolicy",
    "IntentType",
    "NativeOperation",
    "NativeOperationKind",
    "PlannerDecisionTrace",
    "ScenarioPlan",
    "ScriptExecutionPlan",
    "ScriptSetupPlan",
    "ScriptStepPlan",

    # 评审模型
    "ReviewResult",
    "ReviewAllResult",
    "ReviewDimensions",
    "ReviewComment",
    "RequirementReviewDetail",
    "CommentType",
    "CommentSeverity",
    "BenchmarkCase",
    "ExecutionFailureCategory",
    "FailureAnalysisResult",
    "RunManifest",

    # 配置模型
    "LLMConfig",
    "TestConfig",
    "AllureConfig",
    "LogConfig",
    "WorkflowConfig",
    "ProjectSettings",
    "get_settings",

    # LLM 响应模型
    "Message",
    "MessageRole",
    "ChatResponse",
    "TokenUsage",
    "FinishReason",
]
