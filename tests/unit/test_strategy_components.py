"""Tests for strategy planning shared components."""

import pytest

from core.agents.strategy.keywords import StrategyKeywords
from core.agents.strategy.utils import StrategyUtils
from core.agents.strategy.focus_classifier import FocusPointClassifier
from core.agents.strategy.fallback_builder import FallbackStrategyBuilder
from core.models.requirement import Requirement, Priority, RequirementType
from core.models.test_strategy import FocusLevel, ExecutionMode, CoverageAxis


class TestStrategyKeywords:
    """Tests for StrategyKeywords class."""

    def test_critical_keywords_contains_payment(self):
        """Critical keywords should contain payment-related terms."""
        assert "payment" in StrategyKeywords.CRITICAL_KEYWORDS
        assert "pay" in StrategyKeywords.CRITICAL_KEYWORDS
        assert "refund" in StrategyKeywords.CRITICAL_KEYWORDS

    def test_critical_keywords_contains_chinese(self):
        """Critical keywords should contain Chinese terms."""
        assert "支付" in StrategyKeywords.CRITICAL_KEYWORDS
        assert "付款" in StrategyKeywords.CRITICAL_KEYWORDS
        assert "权限" in StrategyKeywords.CRITICAL_KEYWORDS

    def test_major_keywords_contains_failure_terms(self):
        """Major keywords should contain failure-related terms."""
        assert "fail" in StrategyKeywords.MAJOR_KEYWORDS
        assert "error" in StrategyKeywords.MAJOR_KEYWORDS
        assert "exception" in StrategyKeywords.MAJOR_KEYWORDS

    def test_light_keywords_contains_ui_terms(self):
        """Light keywords should contain UI-related terms."""
        assert "load" in StrategyKeywords.LIGHT_KEYWORDS
        assert "visible" in StrategyKeywords.LIGHT_KEYWORDS
        assert "display" in StrategyKeywords.LIGHT_KEYWORDS

    def test_all_keywords_are_tuples(self):
        """All keyword definitions should be immutable tuples."""
        assert isinstance(StrategyKeywords.CRITICAL_KEYWORDS, tuple)
        assert isinstance(StrategyKeywords.MAJOR_KEYWORDS, tuple)
        assert isinstance(StrategyKeywords.LIGHT_KEYWORDS, tuple)
        assert isinstance(StrategyKeywords.BOUNDARY_KEYWORDS, tuple)
        assert isinstance(StrategyKeywords.LOGIN_KEYWORDS, tuple)

    def test_payment_keywords_subset_of_critical(self):
        """Payment keywords should be a subset of critical keywords."""
        for kw in StrategyKeywords.PAYMENT_KEYWORDS:
            assert kw in StrategyKeywords.CRITICAL_KEYWORDS or kw in ["支付", "付款", "退款"]


class TestStrategyUtils:
    """Tests for StrategyUtils class."""

    def test_contains_any_finds_match(self):
        """contains_any should find matching keywords."""
        text = "支付成功后展示结果"
        assert StrategyUtils.contains_any(text, StrategyKeywords.PAYMENT_KEYWORDS)

    def test_contains_any_no_match(self):
        """contains_any should return False when no match."""
        text = "普通文本内容"
        assert not StrategyUtils.contains_any(text, StrategyKeywords.PAYMENT_KEYWORDS)

    def test_normalize_lowercase(self):
        """normalize should convert to lowercase."""
        assert StrategyUtils.normalize("HELLO World") == "hello world"

    def test_normalize_strips_whitespace(self):
        """normalize should strip whitespace."""
        assert StrategyUtils.normalize("  hello  ") == "hello"

    def test_normalize_handles_none(self):
        """normalize should handle None input."""
        assert StrategyUtils.normalize(None) == ""
        assert StrategyUtils.normalize("") == ""

    def test_is_payment_related(self):
        """is_payment_related should detect payment terms."""
        assert StrategyUtils.is_payment_related("支付退款流程")
        assert StrategyUtils.is_payment_related("payment success")
        assert not StrategyUtils.is_payment_related("普通登录流程")

    def test_is_login_related(self):
        """is_login_related should detect login terms."""
        assert StrategyUtils.is_login_related("用户登录系统")
        assert StrategyUtils.is_login_related("user login page")
        assert not StrategyUtils.is_login_related("支付流程")

    def test_is_order_related(self):
        """is_order_related should detect order terms."""
        assert StrategyUtils.is_order_related("下单购买商品")
        assert StrategyUtils.is_order_related("order checkout")
        assert not StrategyUtils.is_order_related("登录流程")


class TestFocusPointClassifier:
    """Tests for FocusPointClassifier class."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance."""
        return FocusPointClassifier()

    @pytest.fixture
    def sample_requirement(self):
        """Create a sample requirement."""
        return Requirement(
            id="REQ_001",
            title="Payment Flow",
            description="User completes payment successfully",
            priority=Priority.HIGH,
            type=RequirementType.FUNCTIONAL,
            acceptance_criteria=["Payment success shows result"],
            ui_elements=[],
        )

    def test_classify_critical_for_payment(self, classifier, sample_requirement):
        """Payment-related text should be classified as critical."""
        level = classifier.classify_focus_level(
            sample_requirement,
            "支付成功后展示结果",
            [CoverageAxis.HAPPY_PATH],
            multi_flow=False,
        )
        assert level == FocusLevel.CRITICAL

    def test_classify_major_for_failure(self, classifier, sample_requirement):
        """Failure-related text should be classified as major or critical."""
        # Note: "提交" is in CRITICAL_KEYWORDS, so we use a pure failure example
        level = classifier.classify_focus_level(
            sample_requirement,
            "操作失败显示错误提示信息",
            [CoverageAxis.HAPPY_PATH, CoverageAxis.NEGATIVE],
            multi_flow=False,
        )
        assert level == FocusLevel.MAJOR

    def test_classify_light_for_ui(self, classifier, sample_requirement):
        """UI-related text should be classified as light."""
        level = classifier.classify_focus_level(
            sample_requirement,
            "页面加载展示输入控件",
            [CoverageAxis.HAPPY_PATH],
            multi_flow=False,
        )
        assert level == FocusLevel.LIGHT

    def test_classify_execution_mode_critical_is_deep(self, classifier):
        """Critical focus level should have deep execution mode."""
        mode = classifier.classify_execution_mode(FocusLevel.CRITICAL, [CoverageAxis.HAPPY_PATH])
        assert mode == ExecutionMode.DEEP

    def test_classify_execution_mode_major_with_multiple_axes(self, classifier):
        """Major with multiple axes should have deep execution mode."""
        mode = classifier.classify_execution_mode(
            FocusLevel.MAJOR,
            [CoverageAxis.HAPPY_PATH, CoverageAxis.NEGATIVE],
        )
        assert mode == ExecutionMode.DEEP

    def test_classify_execution_mode_light_is_smoke(self, classifier):
        """Light focus level should have smoke execution mode."""
        mode = classifier.classify_execution_mode(FocusLevel.LIGHT, [CoverageAxis.HAPPY_PATH])
        assert mode == ExecutionMode.SMOKE

    def test_derive_coverage_axes_includes_boundary(self, classifier):
        """Boundary keywords should add boundary coverage axis."""
        axes = classifier.derive_coverage_axes("输入边界值测试")
        assert CoverageAxis.BOUNDARY in axes

    def test_derive_coverage_axes_includes_negative(self, classifier):
        """Failure keywords should add negative coverage axis."""
        axes = classifier.derive_coverage_axes("支付失败处理")
        assert CoverageAxis.NEGATIVE in axes

    def test_derive_coverage_axes_default_happy_path(self, classifier):
        """Default coverage axis should be happy_path."""
        axes = classifier.derive_coverage_axes("普通文本")
        assert CoverageAxis.HAPPY_PATH in axes

    def test_focus_level_to_weight(self, classifier):
        """Focus level to weight mapping should be correct."""
        assert classifier.focus_level_to_weight(FocusLevel.CRITICAL) == 3
        assert classifier.focus_level_to_weight(FocusLevel.MAJOR) == 2
        assert classifier.focus_level_to_weight(FocusLevel.NORMAL) == 1
        assert classifier.focus_level_to_weight(FocusLevel.LIGHT) == 1


class TestFallbackStrategyBuilder:
    """Tests for FallbackStrategyBuilder class."""

    @pytest.fixture
    def builder(self):
        """Create a builder instance."""
        return FallbackStrategyBuilder()

    @pytest.fixture
    def payment_requirement(self):
        """Create a payment requirement."""
        return Requirement(
            id="REQ_001",
            title="Payment Flow",
            description="User completes payment process successfully",
            priority=Priority.HIGH,
            type=RequirementType.FUNCTIONAL,
            acceptance_criteria=[
                "Payment success deducts balance correctly",
                "Payment failure shows error message",
            ],
            ui_elements=[],
        )

    @pytest.fixture
    def login_requirement(self):
        """Create a login requirement."""
        return Requirement(
            id="REQ_002",
            title="Login Flow",
            description="User logs in with valid credentials",
            priority=Priority.HIGH,
            type=RequirementType.FUNCTIONAL,
            acceptance_criteria=[
                "Login page loads and displays input fields",
                "Submit valid credentials and login successfully",
            ],
            ui_elements=[],
        )

    def test_build_requirement_strategy_returns_correct_id(self, builder, payment_requirement):
        """Built strategy should have correct requirement ID."""
        strategy = builder.build_requirement_strategy(payment_requirement, multi_flow=False)
        assert strategy.requirement_id == "REQ_001"

    def test_build_requirement_strategy_has_focus_points(self, builder, payment_requirement):
        """Built strategy should have focus points."""
        strategy = builder.build_requirement_strategy(payment_requirement, multi_flow=False)
        assert len(strategy.focus_points) == 2

    def test_payment_requirement_has_critical_risk(self, builder, payment_requirement):
        """Payment requirement should have critical or high risk."""
        strategy = builder.build_requirement_strategy(payment_requirement, multi_flow=False)
        assert strategy.overall_risk in ["critical", "high"]

    def test_calculate_case_contribution_critical_deep(self, builder):
        """Critical + Deep should contribute 3 cases."""
        from core.models.test_strategy import FocusPointStrategy
        point = FocusPointStrategy(
            point_id="REQ_001_P01",
            point_text="Test point",
            focus_level=FocusLevel.CRITICAL,
            execution_mode=ExecutionMode.DEEP,
            coverage_axes=[CoverageAxis.HAPPY_PATH],
            reason="Test reason",
            case_weight=3,
        )
        assert builder.calculate_case_contribution(point) == 3

    def test_calculate_case_contribution_major_standard(self, builder):
        """Major + Standard should contribute 1 case."""
        from core.models.test_strategy import FocusPointStrategy
        point = FocusPointStrategy(
            point_id="REQ_001_P01",
            point_text="Test point",
            focus_level=FocusLevel.MAJOR,
            execution_mode=ExecutionMode.STANDARD,
            coverage_axes=[CoverageAxis.HAPPY_PATH],
            reason="Test reason",
            case_weight=2,
        )
        assert builder.calculate_case_contribution(point) == 1

    def test_calculate_case_contribution_normal(self, builder):
        """Normal should contribute 1 case."""
        from core.models.test_strategy import FocusPointStrategy
        point = FocusPointStrategy(
            point_id="REQ_001_P01",
            point_text="Test point",
            focus_level=FocusLevel.NORMAL,
            execution_mode=ExecutionMode.STANDARD,
            coverage_axes=[CoverageAxis.HAPPY_PATH],
            reason="Test reason",
            case_weight=1,
        )
        assert builder.calculate_case_contribution(point) == 1

    def test_calculate_case_contribution_light(self, builder):
        """Light should contribute 0 cases."""
        from core.models.test_strategy import FocusPointStrategy
        point = FocusPointStrategy(
            point_id="REQ_001_P01",
            point_text="Test point",
            focus_level=FocusLevel.LIGHT,
            execution_mode=ExecutionMode.SMOKE,
            coverage_axes=[CoverageAxis.HAPPY_PATH],
            reason="Test reason",
            case_weight=1,
        )
        assert builder.calculate_case_contribution(point) == 0

    def test_multi_flow_login_downgraded_to_light(self, builder, login_requirement):
        """Login in multi-flow document should be downgraded to light."""
        strategy = builder.build_requirement_strategy(login_requirement, multi_flow=True)
        # First acceptance criterion is about UI loading
        first_point = strategy.focus_points[0]
        assert first_point.focus_level == FocusLevel.LIGHT

    def test_build_from_dict(self, builder):
        """build_from_dict should work with dictionary input."""
        req_dict = {
            "id": "REQ_001",
            "title": "Payment Flow",
            "description": "User completes payment process successfully",
            "priority": "high",
            "type": "functional",
            "acceptance_criteria": ["Payment success shows result"],
            "ui_elements": [],
        }
        strategy = builder.build_from_dict(req_dict, multi_flow=False)
        assert strategy.requirement_id == "REQ_001"
